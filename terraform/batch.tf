# Batch compute environment setup
resource "aws_batch_compute_environment" "webcompat-ml" {
  compute_environment_name = "webcompat-ml"

  compute_resources {
    instance_role = "${aws_iam_instance_profile.ecs_instance_role.arn}"

    instance_type = [
      "m3.medium",
    ]

    max_vcpus = 16
    min_vcpus = 0

    security_group_ids = [
      "${aws_security_group.webcompat-ml-sg.id}",
    ]

    subnets = "${data.aws_subnet_ids.all.ids}"

    type = "EC2"
  }

  service_role = "${aws_iam_role.aws_batch_service_role.arn}"
  type         = "MANAGED"
  depends_on   = ["aws_iam_role_policy_attachment.aws_batch_service_role"]
}

resource "aws_batch_job_queue" "webcompat-classify" {
  name = "webcompat-classification-queue"
  state = "ENABLED"
  priority = 1
  compute_environments = [
    "${aws_batch_compute_environment.webcompat-ml.arn}"
  ]
}

resource "aws_batch_job_definition" "webcompat_classification" {
  name = "webcompat_classification"
  type = "container"

  container_properties = <<CONTAINER_PROPERTIES
{
    "image": "mozillawebcompatml/classify",
    "memory": 2048,
    "vcpus": 1,
    "command": [
        "python", "run_job.py", "-i", "Ref::file_url"
    ]
}
CONTAINER_PROPERTIES
}