.PHONY: help up down logs seed grant-roles clean kind-up kind-down reset

help:
	@echo "Common commands:"
	@echo "  make up           Start Keycloak + Postgres and import realm"
	@echo "  make down         Stop everything"
	@echo "  make logs         Tail Keycloak logs"
	@echo "  make grant-roles  Grant realm-management roles to the service account"
	@echo "  make reset        Full reset (down + delete volumes + up + grant-roles)"
	@echo "  make kind-up      Create a local Kind cluster"
	@echo "  make kind-down    Delete the Kind cluster"
	@echo "  make clean        Remove all local state"

up:
	docker compose up -d
	@echo "Waiting for Keycloak to be ready..."
	@until curl -sf http://localhost:8080/realms/master > /dev/null 2>&1; do sleep 2; done
	@echo "Keycloak is up at http://localhost:8080 (admin / admin)"
	@echo "Now run: make grant-roles"

down:
	docker compose down

logs:
	docker compose logs -f keycloak

grant-roles:
	./keycloak/grant-service-account-roles.sh

reset:
	docker compose down -v
	$(MAKE) up
	$(MAKE) grant-roles

kind-up:
	kind create cluster --config kind/cluster.yaml --name iam-takehome

kind-down:
	kind delete cluster --name iam-takehome

clean: down kind-down
	docker compose down -v
