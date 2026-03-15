import boto3
import json
import math
import os

REGION    = 'us-east-2'
S3_BUCKET = os.environ.get('S3_BUCKET', 'opsguardian-knowledge-base-856567377240')
MODEL_ID  = 'amazon.titan-embed-text-v2:0'

# Minimum similarity score to auto-fix (below this = escalate to human)
SIMILARITY_THRESHOLD = 0.25

bedrock = boto3.client('bedrock-runtime', region_name=REGION)
s3      = boto3.client('s3',              region_name=REGION)

def get_embedding(text):
    """Call Titan Embeddings V2 to convert text to a vector"""
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({"inputText": text})
    )
    body = json.loads(response['body'].read())
    return body['embedding']

def cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two vectors (0 to 1)"""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)

def lambda_handler(event, context):
    print(f"Investigator (RAG) activated. Incident: {event['incident_id']}")

    alarm_type = event['alarm_type']
    alarm_name = event.get('alarm_name', '')

    # Build a natural language description of the alarm
    # This is what gets embedded and compared against runbook vectors
    query_text = f"alarm type {alarm_type} triggered. alarm name: {alarm_name}. infrastructure incident requiring remediation."
    print(f"Query text for embedding: '{query_text}'")

    # ── Step 1: Load embeddings from S3 ──────────────────────────
    try:
        print(f"Loading embeddings from S3: s3://{S3_BUCKET}/embeddings.json")
        response        = s3.get_object(Bucket=S3_BUCKET, Key='embeddings.json')
        embeddings_store = json.loads(response['Body'].read().decode('utf-8'))
        print(f"Loaded {len(embeddings_store)} embedded runbook entries")
    except Exception as e:
        print(f"ERROR loading embeddings: {e}")
        print("Falling back to runbook.json...")
        # Fallback to old runbook if embeddings not found
        try:
            response = s3.get_object(Bucket=S3_BUCKET, Key='runbook.json')
            runbook  = json.loads(response['Body'].read().decode('utf-8'))
            event['runbook']          = runbook
            event['similarity_score'] = 0.5
            event['rag_match_id']     = 'fallback'
            event['status']           = 'RunbookLoaded-Fallback'
            return event
        except Exception as e2:
            raise Exception(f"Both embeddings and runbook failed: {e2}")

    # ── Step 2: Embed the incoming alarm query ────────────────────
    try:
        print("Generating embedding for alarm query...")
        query_vector = get_embedding(query_text)
        print(f"Query embedded: {len(query_vector)} dimensions")
    except Exception as e:
        raise Exception(f"Failed to embed query: {e}")

    # ── Step 3: Cosine similarity search ─────────────────────────
    print("Computing cosine similarity against all runbook entries...")
    results = []

    for entry in embeddings_store:
        score = cosine_similarity(query_vector, entry['vector'])
        results.append({
            'score':      score,
            'id':         entry['id'],
            'alarm_type': entry['alarm_type'],
            'fix':        entry['fix'],
            'severity':   entry['severity'],
            'description': entry['description']
        })
        print(f"  {entry['id']} ({entry['alarm_type']}): {score:.4f}")

    # Sort by similarity score descending
    results.sort(key=lambda x: x['score'], reverse=True)
    best_match = results[0]

    print(f"\nBest match: {best_match['id']} ({best_match['alarm_type']}) "
          f"with score {best_match['score']:.4f} ({best_match['score']*100:.1f}%)")

    # ── Step 4: Threshold check ───────────────────────────────────
    if best_match['score'] < SIMILARITY_THRESHOLD:
        print(f"WARNING: Low confidence match ({best_match['score']:.2f} < {SIMILARITY_THRESHOLD})")
        print("Escalating to human instead of auto-fixing")
        event['status']           = 'LowConfidence-EscalateToHuman'
        event['similarity_score'] = round(best_match['score'], 4)
        event['rag_match_id']     = best_match['id']
        event['runbook']          = {'best_match': best_match}
        event['reasoning']        = (
            f"RAG search found best match '{best_match['alarm_type']}' "
            f"with only {best_match['score']*100:.1f}% confidence — below "
            f"the {SIMILARITY_THRESHOLD*100:.0f}% threshold. Escalating to human."
        )
        raise Exception(f"Low confidence RAG match: {best_match['score']:.2f}")

    # ── Step 5: Return enriched incident with RAG results ─────────
    event['runbook'] = {
        best_match['alarm_type']: best_match['fix']
    }
    event['similarity_score'] = round(best_match['score'], 4)
    event['rag_match_id']     = best_match['id']
    event['rag_severity']     = best_match['severity']
    event['alarm_type']       = best_match['alarm_type']  # use RAG-matched type
    event['status']           = 'RunbookLoaded-RAG'
    event['reasoning']        = (
        f"RAG semantic search matched '{best_match['alarm_type']}' "
        f"with {best_match['score']*100:.1f}% confidence. "
        f"Runbook fix: '{best_match['fix']}'"
    )

    print(f"RAG complete. Returning enriched incident to pipeline.")
    return event