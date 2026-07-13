#!/usr/bin/env bash
# Grants the user-cleanup-service service account the realm-management roles
# it needs to query and delete users.
#
# Keycloak's realm import doesn't reliably attach role mappings to service
# accounts, so we do it after the import via kcadm inside the container.

set -euo pipefail

CONTAINER="${CONTAINER:-iam-takehome-keycloak}"
REALM="${REALM:-acme}"
CLIENT_ID="${CLIENT_ID:-user-cleanup-service}"

echo "Configuring credentials for kcadm..."
docker exec "$CONTAINER" /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password admin

echo "Granting realm-management roles to $CLIENT_ID service account in realm $REALM..."

# Roles the cleanup job actually needs:
#   view-users    - list users, read their attributes
#   manage-users  - update / delete users
ROLES=(view-users manage-users query-users view-events)

for ROLE in "${ROLES[@]}"; do
  echo "  granting $ROLE..."
  docker exec "$CONTAINER" /opt/keycloak/bin/kcadm.sh add-roles \
    -r "$REALM" \
    --uusername "service-account-${CLIENT_ID}" \
    --cclientid realm-management \
    --rolename "$ROLE"
done

echo ""
echo "Done. The $CLIENT_ID service account can now:"
echo "  - list users in the $REALM realm"
echo "  - read their attributes"
echo "  - update and delete users"
echo "  - view auth events"
echo ""
echo "Test with:"
echo "  curl -s -X POST http://localhost:8080/realms/$REALM/protocol/openid-connect/token \\"
echo "    -d grant_type=client_credentials \\"
echo "    -d client_id=$CLIENT_ID \\"
echo "    -d client_secret=cleanup-secret-change-me | jq ."
