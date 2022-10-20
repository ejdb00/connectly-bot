PYTHON_DOCKER_NAME=review-bot
POSTGRES_DOCKER_NAME=review-bot-postgres

.PHONY: pytest
pytest:
	@docker exec -it ${PYTHON_DOCKER_NAME} /bin/bash -c "/usr/src/scripts/run_pytest.sh"

.PHONY: shell
shell:
	@docker exec -it ${PYTHON_DOCKER_NAME} /bin/bash
	
.PHONY: psql
psql:
	@docker exec -it -u postgres ${POSTGRES_DOCKER_NAME} /usr/bin/psql