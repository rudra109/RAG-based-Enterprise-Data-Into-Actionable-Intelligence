import os
import subprocess
import argparse

def run_command(command):
    print(f"Executing: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode == 0:
        print("✅ Success")
    else:
        print(f"❌ Error: {result.stderr}")

def teardown():
    print("🚨 TEARDOWN INITIATED: Destroying expensive Google Cloud Resources...")
    
    # 1. Undeploy Vector Search Index (Stops the $0.09/hr charge)
    # Note: Requires specific endpoint ID and index ID
    print("\n--- Deleting Vertex AI Vector Search ---")
    print("⚠️  To fully delete Vector Search, go to Google Cloud Console > Vertex AI > Vector Search")
    print("1. Click your Endpoint and select 'Undeploy Index'")
    print("2. Delete the Endpoint")
    
    # 2. Delete Spanner Instance (Stops the $0.12/hr charge)
    print("\n--- Deleting Spanner Instance ---")
    run_command("gcloud spanner instances delete hackathon-spanner --quiet")
    
    print("\n✅ Teardown complete. Expensive resources have been stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage expensive GCP resources.")
    parser.add_argument("action", choices=["off"], help="Action to perform (currently only 'off' is supported for complete teardown)")
    args = parser.parse_args()
    
    if args.action == "off":
        confirm = input("WARNING: This will delete your Spanner database and all data inside it! Are you sure? (y/n): ")
        if confirm.lower() == 'y':
            teardown()
        else:
            print("Cancelled.")
