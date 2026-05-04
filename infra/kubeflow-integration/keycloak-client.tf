# Terraform/OpenTofu configuration for registering the AI Platform
# as an OIDC client in the Kubeflow Keycloak realm.
#
# Usage: Apply this alongside the Kubeflow4x Keycloak module,
# or run standalone against the same Keycloak instance.

variable "keycloak_url" {
  description = "Keycloak base URL"
  type        = string
}

variable "keycloak_realm" {
  description = "Keycloak realm name"
  type        = string
  default     = "kubeflow-4x"
}

variable "ai_platform_url" {
  description = "AI Platform base URL"
  type        = string
}

variable "ai_platform_client_id" {
  description = "OIDC client ID for AI Platform"
  type        = string
  default     = "enterprise-ai-web"
}

terraform {
  required_providers {
    keycloak = {
      source  = "mrparkers/keycloak"
      version = ">= 5.0.0"
    }
  }
}

data "keycloak_realm" "kf4x" {
  realm = var.keycloak_realm
}

resource "keycloak_openid_client" "ai_platform" {
  realm_id  = data.keycloak_realm.kf4x.id
  client_id = var.ai_platform_client_id
  name      = "Enterprise AI Platform"

  enabled                      = true
  access_type                  = "CONFIDENTIAL"
  standard_flow_enabled        = true
  direct_access_grants_enabled = false
  implicit_flow_enabled        = false

  root_url  = var.ai_platform_url
  base_url  = var.ai_platform_url
  admin_url = var.ai_platform_url

  valid_redirect_uris = [
    "${var.ai_platform_url}/*",
  ]

  valid_post_logout_redirect_uris = [
    "${var.ai_platform_url}/*",
  ]

  web_origins = ["+"]
}

resource "keycloak_openid_client_default_scopes" "ai_platform_scopes" {
  realm_id  = data.keycloak_realm.kf4x.id
  client_id = keycloak_openid_client.ai_platform.id

  default_scopes = [
    "openid",
    "profile",
    "email",
    "groups",
  ]
}

# Map tenant_id claim from user attribute
resource "keycloak_openid_user_attribute_protocol_mapper" "tenant_id" {
  realm_id  = data.keycloak_realm.kf4x.id
  client_id = keycloak_openid_client.ai_platform.id
  name      = "tenant-id-mapper"

  user_attribute   = "tenant_id"
  claim_name       = "tenant_id"
  claim_value_type = "String"

  add_to_id_token     = true
  add_to_access_token = true
  add_to_userinfo     = true
}

output "client_id" {
  value = keycloak_openid_client.ai_platform.client_id
}

output "client_secret" {
  value     = keycloak_openid_client.ai_platform.client_secret
  sensitive = true
}
