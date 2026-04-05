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
