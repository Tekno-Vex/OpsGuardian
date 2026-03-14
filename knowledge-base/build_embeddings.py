import boto3
import json
import math
import os

# ── CONFIG ──────────────────────────────────────────────────────
REGION      = 'us-east-2'
S3_BUCKET   = 'opsguardian-knowledge-base-856567377240'  # e.g. opsguardian-knowledge-base-856567377240
MODEL_ID    = 'amazon.titan-embed-text-v2:0'
INPUT_FILE  = 'runbook_rich.json'
OUTPUT_FILE = 'embeddings.json'
# ────────────────────────────────────────────────────────────────

bedrock = boto3.client('bedrock-runtime', region_name=REGION)
s3      = boto3.client('s3',              region_name=REGION)

def get_embedding(text):
    """Call Titan Embeddings V2 and return a vector"""
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({"inputText": text})
    )
    body = json.loads(response['body'].read())
    return body['embedding']

def cosine_similarity(vec_a, vec_b):
    """Compute cosine similarity between two vectors"""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    return dot_product / (magnitude_a * magnitude_b)

def main():
    # Load the rich runbook
    print("Loading runbook_rich.json...")
    with open(INPUT_FILE, 'r') as f:
        runbook = json.load(f)

    print(f"Found {len(runbook)} runbook entries. Generating embeddings...")
    print("This will make one Bedrock API call per entry.\n")

    embeddings_store = []

    for i, entry in enumerate(runbook):
        # Combine description + symptoms into one searchable text
        search_text = f"{entry['description']} {entry['symptoms']}"
        print(f"[{i+1}/{len(runbook)}] Embedding: {entry['id']} ({entry['alarm_type']})...")

        vector = get_embedding(search_text)

        embeddings_store.append({
            'id':          entry['id'],
            'alarm_type':  entry['alarm_type'],
            'description': entry['description'],
            'symptoms':    entry['symptoms'],
            'fix':         entry['fix'],
            'severity':    entry['severity'],
            'vector':      vector
        })

        print(f"  ✓ Vector generated: {len(vector)} dimensions")

    # Save locally
    print(f"\nSaving {OUTPUT_FILE} locally...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(embeddings_store, f)
    print(f"✓ Saved {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE)} bytes)")

    # Upload to S3
    print(f"\nUploading to S3: s3://{S3_BUCKET}/embeddings.json ...")
    s3.upload_file(OUTPUT_FILE, S3_BUCKET, 'embeddings.json')
    print("✓ Uploaded to S3 successfully!")

    # Quick self-test
    print("\n--- Self-Test: Semantic Search ---")
    test_query = "server is overloaded and unresponsive"
    print(f"Test query: '{test_query}'")

    query_vector = get_embedding(test_query)

    results = []
    for entry in embeddings_store:
        score = cosine_similarity(query_vector, entry['vector'])
        results.append((score, entry['alarm_type'], entry['fix']))

    results.sort(reverse=True)
    print("\nTop matches:")
    for score, alarm_type, fix in results[:3]:
        print(f"  {score:.4f} ({score*100:.1f}%) → {alarm_type}: {fix}")

    print("\n✅ Sprint 6 embedding build complete!")
    print(f"   embeddings.json uploaded to s3://{S3_BUCKET}/embeddings.json")

if __name__ == '__main__':
    main()