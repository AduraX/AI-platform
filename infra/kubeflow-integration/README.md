# Kubeflow Integration

This directory contains resources to integrate the Enterprise AI Platform
with a Kubeflow4x Phase-1 deployment that uses Keycloak for authentication.

## Prerequisites

- Kubeflow4x Phase-1 deployed with Keycloak
- Istio service mesh with oauth2-proxy ExtAuthz configured
- Access to the Keycloak admin API or Terraform state

## Setup

### 1. Register OIDC Client in Keycloak

Apply the Terraform configuration to create the AI Platform client:

```bash
cd infra/kubeflow-integration
terraform init
terraform apply \
  -var="keycloak_url=https://keycloak.example.com" \
  -var="ai_platform_url=https://ai-platform.example.com"
```

### 2. Update Secrets

Update `infra/kubernetes/base/secrets.yaml` with the client ID and secret
from Terraform output.

### 3. Deploy

```bash
# Development
kubectl apply -k infra/kubernetes/overlays/dev

# Production (with Istio integration)
kubectl apply -k infra/kubeflow-integration
```

### 4. Istio Configuration

The `istio-auth.yaml` configures:
- **RequestAuthentication**: Validates JWTs from Keycloak
- **AuthorizationPolicy (DENY)**: Rejects unauthenticated requests (except /health, /metrics)
- **AuthorizationPolicy (CUSTOM)**: Delegates to oauth2-proxy for browser flows

Replace `__KEYCLOAK_ISSUER__` and `__KEYCLOAK_JWKS_URI__` in `istio-auth.yaml`
with your Keycloak realm URLs.

## Architecture

```
Browser -> Istio Ingress Gateway -> oauth2-proxy -> Keycloak
                |
        VirtualService routes:
        /api/v1/* -> api-gateway:8000
        /*        -> frontend:3000
                |
        Internal services (ClusterIP)
```
