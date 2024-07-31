resource "aws_s3_bucket" "attachments" {
  bucket = "attachments"
}

resource "aws_s3_bucket_ownership_controls" "attachments" {
  bucket = aws_s3_bucket.attachments.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_public_access_block" "attachments" {
  bucket = aws_s3_bucket.attachments.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_acl" "attachments" {
  depends_on = [
    aws_s3_bucket_ownership_controls.attachments,
    aws_s3_bucket_public_access_block.attachments
  ]

  bucket = aws_s3_bucket.attachments.id
  acl    = "public-read"
}
