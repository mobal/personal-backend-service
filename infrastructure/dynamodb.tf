resource "aws_dynamodb_table" "posts" {
  name         = "${var.stage}-posts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "post_path"
    type = "S"
  }

  attribute {
    name = "title"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "PostPathIndex"

    key_schema {
      attribute_name = "post_path"
      key_type       = "HASH"
    }

    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "TitleIndex"

    key_schema {
      attribute_name = "title"
      key_type       = "HASH"
    }

    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "CreatedAtIndex"

    key_schema {
      attribute_name = "created_at"
      key_type       = "HASH"
    }

    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "rate_limits" {
  name         = "${var.stage}-rate-limits"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "client_id"
  range_key    = "endpoint"

  attribute {
    name = "client_id"
    type = "S"
  }

  attribute {
    name = "endpoint"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}
