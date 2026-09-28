output "backend_ecr_repository_url" {
  description = "URL of the ECR repository that stores Terris backend images."
  value       = aws_ecr_repository.backend.repository_url
}

output "github_actions_role_arn" {
  description = "ARN of the IAM role assumed by Terris GitHub Actions through OIDC."
  value       = aws_iam_role.github_actions.arn
}

output "github_actions_oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider."
  value       = aws_iam_openid_connect_provider.github_actions.arn
}

output "vpc_id" {
  description = "ID of the Terris VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the Terris public subnet."
  value       = aws_subnet.public.id
}

output "backend_security_group_id" {
  description = "ID of the security group for the Terris backend host."
  value       = aws_security_group.backend.id
}

output "backend_iam_role_name" {
  description = "Name of the IAM role used by the Terris backend EC2 instance."
  value       = aws_iam_role.backend.name
}

output "backend_instance_profile_name" {
  description = "Name of the instance profile for the Terris backend EC2 instance."
  value       = aws_iam_instance_profile.backend.name
}

output "backend_instance_id" {
  description = "ID of the Terris backend EC2 instance."
  value       = aws_instance.backend.id
}

output "backend_public_ip" {
  description = "Stable Elastic IP address assigned to the Terris backend host."
  value       = aws_eip.backend.public_ip
}

output "backend_public_dns" {
  description = "Public DNS hostname associated with the backend Elastic IP."
  value       = aws_eip.backend.public_dns
}

output "frontend_bucket_name" {
  description = "Name of the private S3 bucket containing the Terris frontend."
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_arn" {
  description = "ARN of the private Terris frontend bucket."
  value       = aws_s3_bucket.frontend.arn
}

output "cloudfront_distribution_id" {
  description = "ID of the Terris CloudFront distribution."
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_domain_name" {
  description = "CloudFront domain serving the Terris frontend and API."
  value       = aws_cloudfront_distribution.main.domain_name
}

output "cloudfront_url" {
  description = "HTTPS URL of the Terris CloudFront distribution."
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}
