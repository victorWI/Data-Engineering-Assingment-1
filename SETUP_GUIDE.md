# Setup guide: from an empty Google Cloud project to a working demo

Total time is about 1.5–2 hours, most of it waiting for builds. You never need a Vertex AI
Workbench notebook (the expensive VM from Lab 4). The pipeline is compiled and submitted by
Cloud Build.

Each command block is meant for **Cloud Shell**: the `>_` icon at the top right of the Google Cloud
console. Copy and paste the blocks in order.

---

## 0. What you need

- A Google Cloud project with billing enabled (use your course credits/coupon).
- A GitHub account.

## 1. Put the code on GitHub

1. On github.com create a **new repository**, e.g. `coffee-mlops`. Public or private are both
   fine. If private, go to *Settings → Collaborators* and add **IndikaKuma** (required by the brief).
2. Upload this folder to it. From a terminal on your laptop, inside the unzipped folder:

```bash
git init -b main
git add .
git commit -m "Coffee liking MLOps system"
git remote add origin https://github.com/<your-username>/coffee-mlops.git
git push -u origin main
```

(If you don't use git yet: on the empty repo page, click *uploading an existing file* and drag in
the folder contents. Using git is better, because the demo relies on pushing changes.)

## 2. Set your variables (Cloud Shell)

Open Cloud Shell and set these once. **Change `SUFFIX`** to something unique, e.g. your student number.
Bucket names are global, so they must be unique.

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export REGION=us-central1
export SUFFIX=CHANGE_ME_123456
export DATA_BUCKET=coffee-data-$SUFFIX
export MODEL_BUCKET=coffee-models-$SUFFIX
export TEMP_BUCKET=coffee-temp-$SUFFIX
export SA=$PROJECT_NUMBER-compute@developer.gserviceaccount.com
echo "$PROJECT_ID / $DATA_BUCKET / $MODEL_BUCKET / $TEMP_BUCKET / $SA"
```

> If Cloud Shell restarts later, run this block again. Variables are not kept between sessions.

## 3. Enable the services

```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com storage.googleapis.com pubsub.googleapis.com compute.googleapis.com \
  iam.googleapis.com cloudresourcemanager.googleapis.com secretmanager.googleapis.com
```

(Secret Manager is needed because the GitHub connection in step 7 stores its token there.)

## 4. Create the Docker image repository and the three buckets

```bash
gcloud artifacts repositories create coffee-repo --repository-format=docker --location=$REGION

gcloud storage buckets create gs://$DATA_BUCKET  --location=$REGION
gcloud storage buckets create gs://$MODEL_BUCKET --location=$REGION
gcloud storage buckets create gs://$TEMP_BUCKET  --location=$REGION
```

Keep everything in `us-central1`. The labs warn that mixing regions causes permission errors.

## 5. Give the build service account its permissions

Cloud Build triggers and Vertex AI pipelines run as the Compute Engine default service account
(`$SA`). In new projects it starts without permissions, so grant them:

```bash
for ROLE in roles/cloudbuild.builds.builder roles/run.admin roles/iam.serviceAccountUser \
            roles/storage.admin roles/artifactregistry.writer roles/aiplatform.user \
            roles/logging.logWriter roles/pubsub.subscriber; do
  gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$SA --role=$ROLE --condition=None -q > /dev/null
  echo "granted $ROLE"
done
```

## 6. Pub/Sub: notify Cloud Build when a new production model appears

```bash
gcloud pubsub topics create coffee-model-updates

# allow Cloud Storage to publish to that topic
GCS_AGENT=service-$PROJECT_NUMBER@gs-project-accounts.iam.gserviceaccount.com
gcloud pubsub topics add-iam-policy-binding coffee-model-updates \
  --member=serviceAccount:$GCS_AGENT --role=roles/pubsub.publisher

# send a message whenever production/model.pkl is (re)written in the model bucket
gcloud storage buckets notifications create gs://$MODEL_BUCKET --topic=coffee-model-updates \
  --event-types=OBJECT_FINALIZE --object-prefix=production/model.pkl
```

## 7. Connect GitHub to Cloud Build (console)

1. Console → **Cloud Build → Repositories → 2nd gen** tab → **Create host connection**.
2. Provider **GitHub**, region **us-central1**, name e.g. `github`. Click *Connect*, sign in to
   GitHub and install the Google Cloud Build app on your `coffee-mlops` repository.
   If it offers an *existing installation*, only pick it when it belongs to the GitHub account
   that owns the repository; otherwise choose *Install in a new account*. If asked to grant the
   Secret Manager Admin role to the Cloud Build service agent, click *Grant*.
3. Back on the Repositories page, click **Link repository**, choose the connection and your
   `coffee-mlops` repo.

## 8. Create the four triggers (console)

Console → **Cloud Build → Triggers** → **Create trigger** for each row below, choosing
**Region: us-central1** inside the form. Create `deploy-on-new-model` **before** the first training
run, otherwise the first "new model" message has no listener. For all four:

- **Repository generation:** 2nd gen, with your repo selected.
- **Service account:** choose `…-compute@developer.gserviceaccount.com`.

**Substitution variables:** add them under *Advanced → Substitution variables*. Use your real
bucket names, the ones `echo`ed in step 2.

| Trigger name | Event | Branch / filters | Configuration file | Substitutions |
|---|---|---|---|---|
| `build-pipeline-executor` | **Manual invocation** | branch `^main$` | `cloudbuild/pipeline-executor-build.yaml` | none needed |
| `continuous-training` | **Push to a branch** | branch `^main$`; *Included files filter*: `data/incoming/**` and `ml-pipeline/**` | `cloudbuild/training-cicd.yaml` | `_DATA_REPO`, `_MODEL_REPO`, `_TEMP_REPO` |
| `deploy-on-new-model` | **Pub/Sub message**, topic `coffee-model-updates` | branch `main` (*Revision* → Branch) | `cloudbuild/model-deployment-cicd.yaml` | `_MODEL_REPO` |
| `deploy-on-app-change` | **Push to a branch** | branch `^main$`; *Included files filter*: `prediction-api/**` and `prediction-ui/**` | `cloudbuild/model-deployment-cicd.yaml` | `_MODEL_REPO` |

`_LOCATION` (`us-central1`) and `_REPOSITORY` (`coffee-repo`) have defaults in the files, so you
only need to set them if you changed those names.

## 9. First run

1. **Build the executor tool:** on the Triggers page, click **Run** on `build-pipeline-executor`.
   It takes about 2 minutes. Check *Artifact Registry → coffee-repo*: a `pipeline-executor` image appears.
2. **Train the first model:** click **Run** on `continuous-training`. Open *Cloud Build → History*
   to follow it. The last step waits for Vertex AI, which takes about 10–15 minutes. Watch the
   graph in **Vertex AI → Pipelines**. There is no production model yet, so the `challenger-wins`
   branch runs and `production/model.pkl` appears in the model bucket.
3. **Automatic deployment:** that upload fires `deploy-on-new-model` without you doing anything.
   It takes about 5 minutes. When it's done, the last step (`smoke-test`) prints a prediction from
   the live API.
4. **Open the app:** *Cloud Run → coffee-prediction-ui →* click the URL. Fill in a cup and press
   *Predict*. `…coffee-prediction-api URL/health` shows which model version is being served.

## 10. Demo script (Friday)

The brief asks you to run continuous training and deployment through CI/CD during the demo. One
full cycle takes about 20 minutes, longer than your 15-minute slot, so **record a video of steps
B–C beforehand** and play it. Then do A and D live.

- **A. Use the app (live):** open the UI and predict two contrasting cups. Show `/health`
  (current model version and accuracy).
- **B. New data → retraining → redeployment (video):**
  ```bash
  cp data/source/week_2.csv data/incoming/
  git add data/incoming && git commit -m "Add week 2 tasting data" && git push
  ```
  Show:
  - `continuous-training` starting by itself;
  - the Vertex AI pipeline graph and the metrics of `evaluate-vs-champion`, where the challenger beats the champion;
  - `deploy-on-new-model` starting by itself;
  - `/health` showing the new version.
- **C. A model that is *not* better (video):** click **Run** on `continuous-training` again
  without new data. The new model ties the production model, so `evaluate-vs-champion` says
  `KEEP`, the `challenger-wins` branch is skipped, and nothing is redeployed.
- **D. App change → CI/CD (live, or video):** change a text in
  `prediction-ui/templates/index.html`, then commit and push. `deploy-on-app-change` rebuilds
  and redeploys.
- **E. Walk through the code:**
  - `ml-pipeline/coffee_training_pipeline.py`: the components and the `dsl.If` branch;
  - `prediction-api/coffee_predictor.py`;
  - the three files in `cloudbuild/`.

You can add `week_3.csv` the same way for a third round.

**Optional extra (scheduled retraining):** *Cloud Build → Triggers → `continuous-training` → ⋮ →
Run on schedule*. Lab 3 live showed this with Cloud Scheduler.

## 11. Costs and clean-up

- Cloud Run scales to zero when nobody uses it, so it costs close to nothing.
- Each pipeline run costs a few cents.
- Don't create Vertex AI Endpoints or Workbench notebooks; this project doesn't need them.
- After grading:
  - delete the two Cloud Run services and the buckets;
  - disable the push triggers so a stray commit doesn't start builds.

## 12. If something fails

| Symptom | Fix |
|---|---|
| Trigger says it needs a service account | Select `…-compute@developer.gserviceaccount.com` in the trigger (step 8) |
| `PERMISSION_DENIED` in a build step | Rerun the role block in step 5 and wait a minute (IAM changes take time) |
| `run-pipeline` step: image not found | Run `build-pipeline-executor` first (step 9.1) |
| `run-pipeline` fails | Open the failed run in Vertex AI → Pipelines, click the red step, then *View logs* |
| Deployment didn't start after training | Check the model bucket has `production/model.pkl`, then check step 6. Run `gcloud storage buckets notifications list gs://$MODEL_BUCKET` |
| UI says the prediction service can't be reached | Open the API URL + `/health` directly. If that fails, look at *Cloud Run → coffee-prediction-api → Logs* |
| Push didn't start a build | The push must touch a path in the trigger's *Included files filter* |
