.PHONY: help up down logs seed grant-roles clean kind-up kind-down reset run \
	helm-lint helm-template image-build helm-install helm-test helm-uninstall

IMAGE_NAME ?= cleaner
IMAGE_TAG ?= 0.1.0
HELM_RELEASE ?= keycloak-cleaner
HELM_NAMESPACE ?= keycloak-cleaner
KIND_CLUSTER ?= iam-takehome

help:
	@echo "Common commands:"
	@echo "  make up              Start Keycloak + Postgres, import realm, seed login data"
	@echo "  make down            Stop everything"
	@echo "  make logs            Tail Keycloak logs"
	@echo "  make seed            Re-seed lastLogin attributes + LOGIN events (relative to now)"
	@echo "  make grant-roles     Grant realm-management roles to the service account"
	@echo "  make run             Run the Python cleaner locally (no Kubernetes)"
	@echo "  make reset           Full reset (down + delete volumes + up + grant-roles)"
	@echo "  make kind-up         Create a local Kind cluster"
	@echo "  make kind-down       Delete the Kind cluster"
	@echo "  make clean           Remove all local state"
	@echo ""
	@echo "Helm / Kind testing:"
	@echo "  make helm-lint       Lint the Helm chart"
	@echo "  make helm-template   Render the chart locally"
	@echo "  make image-build     Build the cleaner container image"
	@echo "  make helm-install    Install chart into Kind (requires kind-up + image-build)"
	@echo "  make helm-test       End-to-end test: up, kind, install, manual job, logs"
	@echo "  make helm-uninstall  Remove the Helm release"

up:
	docker compose up -d
	@echo "Waiting for Keycloak to be ready..."
	@until curl -sf http://localhost:8080/realms/acme > /dev/null 2>&1; do sleep 2; done
	@$(MAKE) seed
	@echo "Keycloak is up at http://localhost:8080 (admin / admin)"
	@echo "Now run: make grant-roles"

seed:
	./keycloak/seed.sh

down:
	docker compose down

logs:
	docker compose logs -f keycloak

grant-roles:
	./keycloak/grant-service-account-roles.sh

run:
	PYTHONPATH=src python3 -m cleaner.main

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

helm-lint:
	helm lint ./deploy/keycloak-cleaner

helm-template:
	helm template $(HELM_RELEASE) ./deploy/keycloak-cleaner -n $(HELM_NAMESPACE)

image-build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

helm-install: kind-up image-build
	kind load docker-image $(IMAGE_NAME):$(IMAGE_TAG) --name $(KIND_CLUSTER)
	kubectl create namespace $(HELM_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	helm upgrade --install $(HELM_RELEASE) ./deploy/keycloak-cleaner \
		-n $(HELM_NAMESPACE) \
		-f ./deploy/keycloak-cleaner/values-kind.yaml \
		--set image.repository=$(IMAGE_NAME) \
		--set image.tag=$(IMAGE_TAG) \
		--wait --timeout 120s

helm-uninstall:
	helm uninstall $(HELM_RELEASE) -n $(HELM_NAMESPACE) || true

helm-test: up grant-roles helm-install
	@JOB=$(HELM_RELEASE)-manual-$$(date +%s); \
	kubectl create job --from=cronjob/$(HELM_RELEASE) $$JOB -n $(HELM_NAMESPACE); \
	echo "Waiting for job $$JOB..."; \
	kubectl wait --for=condition=complete job/$$JOB -n $(HELM_NAMESPACE) --timeout=120s; \
	echo "Job logs:"; \
	kubectl logs -n $(HELM_NAMESPACE) job/$$JOB
