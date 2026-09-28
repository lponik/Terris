data "aws_ssm_parameter" "amazon_linux_2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_instance" "backend" {
  ami                         = data.aws_ssm_parameter.amazon_linux_2023_ami.value
  instance_type               = var.backend_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.backend.id]
  iam_instance_profile        = aws_iam_instance_profile.backend.name
  associate_public_ip_address = true

  user_data                   = file("${path.module}/user_data.sh")
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_type = "gp3"
    volume_size = 12
    encrypted   = true
  }

  tags = {
    Name    = "${var.project_name}-backend"
    Project = var.project_name
  }
}

resource "aws_eip" "backend" {
  domain   = "vpc"
  instance = aws_instance.backend.id

  tags = {
    Name    = "${var.project_name}-backend-eip"
    Project = var.project_name
  }

  depends_on = [aws_internet_gateway.main]
}