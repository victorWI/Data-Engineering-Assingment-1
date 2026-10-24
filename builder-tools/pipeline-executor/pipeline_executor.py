"""
Submit a compiled Vertex AI pipeline (YAML) and wait until it finishes.

Used as a custom Cloud Build step in cloudbuild/training-cicd.yaml.
Adapted from DE2026 lab4/custom_cloud_build_builder_tools/pipeline_executor (Dr. Indika Kumara).
"""
import argparse
import json
import logging
import sys

import google.cloud.aiplatform as aip


def run_pipeline_job(name, pipeline_def, pipeline_root, parameter_dict, project, region):
    with open(parameter_dict) as f:
        parameters = json.load(f)
    logging.info("Pipeline parameters: %s", parameters)

    aip.init(project=project, location=region)
    job = aip.PipelineJob(
        display_name=name,
        enable_caching=False,  # always re-run every step so new data is really used
        template_path=pipeline_def,
        pipeline_root=pipeline_root,
        parameter_values=parameters,
    )
    # run() blocks until the pipeline ends and raises an error if it fails,
    # so a failed training run also fails the Cloud Build pipeline.
    job.run()
    logging.info("Pipeline finished with state %s", job.state)


def parse_command_line_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Display name of the pipeline run")
    parser.add_argument("--pipeline_def", required=True, help="Compiled pipeline YAML file")
    parser.add_argument("--pipeline_root", required=True, help="gs:// folder for pipeline artifacts")
    parser.add_argument("--parameter_dict", required=True, help="JSON file with pipeline parameters")
    parser.add_argument("--project", required=True, help="Google Cloud project ID")
    parser.add_argument("--region", default="us-central1", help="Vertex AI region")
    return vars(parser.parse_args())


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    run_pipeline_job(**parse_command_line_arguments())
