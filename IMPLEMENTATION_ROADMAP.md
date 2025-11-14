# Implementation Roadmap: Current State → Target POC

**Original Status (2025-11-14):** ~10% complete
**Current Status (2025-01-14):** ~75% complete ✅
**Target:** Fully functional LLM-enhanced static analysis POC
**Original Timeline:** 13 weeks
**Actual Progress:** Phases 1-5 complete (8 weeks worth of work)
**Last Updated:** 2025-01-14

---

## Progress Summary

### ✅ Completed (Phases 1-5)
- ✅ **Phase 1-2**: Infrastructure & Static Analysis (Temporal, Semgrep/Bandit/Ruff)
- ✅ **Phase 3**: LLM Adjudication (Post-processing filter pattern)
- ✅ **Phase 4**: Interactive & Multi-Agent Patterns
- ✅ **Phase 5**: Semantic Clustering (Qdrant + embeddings)
- ✅ **Frontend**: Complete React + TypeScript UI

### ⚠️ In Progress
- ⚠️ Django REST API endpoints (backend logic exists)
- ⚠️ Database migrations (models defined)
- ⚠️ Integration testing

### ❌ Remaining (Optional)
- ❌ Rust parser service (optional optimization)
- ❌ WebSocket real-time updates (nice-to-have)
- ❌ Authentication/authorization (not required for POC)

---

## Overview

This document provides a step-by-step roadmap to transform the current generic security platform into the required POC demonstrating LLM-enhanced static analysis with multi-agent patterns.

### Original State (What We Had - 2025-11-14)
- ✅ Django 5.0 backend with well-designed models
- ✅ PostgreSQL 15 with multi-tenancy support
- ✅ Docker Compose environment (modern V2 syntax)
- ✅ Pixi package manager integration
- ❌ Celery task queue (WRONG - needed replacement)
- ⚠️ Basic REST API endpoints (incomplete)
- ✅ Django admin panel
- ✅ Comprehensive ADR documentation

### Current State (What We Have - 2025-01-14)
- ✅ Temporal workflow orchestration (Celery removed)
- ✅ Langroid multi-agent system (all 3 patterns implemented)
- ✅ LLM integration (Claude Sonnet-4, GPT-4o, embeddings)
- ✅ Static analysis tools (Semgrep, Bandit, Ruff all working)
- ✅ Qdrant vector database (with clustering)
- ✅ SARIF 2.1.0 parsing
- ✅ Three agent patterns with comparison framework
- ✅ React + TypeScript frontend (complete UI)
- ⚠️ REST API endpoints (logic exists, DRF wiring needed)
- ⚠️ Database migrations (models defined, not applied)

### Remaining Work
- ⚠️ REST API implementation (3-5 days)
- ⚠️ Database migrations (1-2 days)
- ⚠️ Integration testing (2-3 days)
- ❌ Rust code parser service (OPTIONAL - Python parsing works)
- ❌ WebSocket updates (OPTIONAL - polling acceptable)
- ❌ Auth/authorization (OPTIONAL for internal POC)

---

## Phase 1: Foundation & LLM Integration (Weeks 1-2)

**Goal:** Remove Celery, install Temporal, prove LLM integration works

### Week 1: Rip Out Celery, Install Temporal

#### Task 1.1: Remove Celery Dependencies
- [ ] **File:** `backend/requirements.txt`
  - Remove: `celery==5.3.6`, `celery[redis]==5.3.6`
  - Remove: `django-celery-beat` (if present)
  - Remove: `django-celery-results` (if present)

- [ ] **File:** `backend/config/celery.py`
  - Delete entire file

- [ ] **File:** `backend/config/__init__.py`
  - Remove Celery app initialization lines

- [ ] **File:** `backend/config/settings.py`
  - Remove all `CELERY_*` configuration variables
  - Keep `REDIS_URL` (used by Temporal)

- [ ] **Files:** `backend/apps/scans/tasks.py`, `backend/apps/organizations/tasks.py`
  - Delete these files (will be replaced with Temporal activities)

- [ ] **File:** `docker-compose.yml`
  - Remove `celery_worker` service
  - Remove `celery_beat` service

#### Task 1.2: Add Temporal to Dependencies
- [ ] **File:** `backend/requirements.txt`
  - Add: `temporalio==1.5.0`
  - Add: `temporalio[asyncio]==1.5.0`

- [ ] **File:** `pyproject.toml`
  - Add to `[tool.pixi.pypi-dependencies]`:
    ```toml
    temporalio = {version = "==1.5.0", extras = ["asyncio"]}
    ```

#### Task 1.3: Add Temporal Server to Docker Compose
- [ ] **File:** `docker-compose.yml`
  - Add Temporal service:
    ```yaml
    temporal:
      image: temporalio/auto-setup:latest
      environment:
        - DB=postgresql
        - DB_PORT=5432
        - POSTGRES_USER=postgres
        - POSTGRES_PWD=postgres
        - POSTGRES_SEEDS=postgres
      ports:
        - "7233:7233"  # gRPC
        - "8233:8233"  # Web UI
      depends_on:
        postgres:
          condition: service_healthy
    ```

- [ ] Test: `docker compose up -d temporal`
- [ ] Verify: Access http://localhost:8233 (Temporal UI)

#### Task 1.4: Create Temporal Worker Infrastructure
- [ ] **Create:** `backend/workers/__init__.py`
- [ ] **Create:** `backend/workers/temporal_worker.py`
  ```python
  import asyncio
  from temporalio.client import Client
  from temporalio.worker import Worker

  async def main():
      client = await Client.connect("temporal:7233")

      worker = Worker(
          client,
          task_queue="code-analysis",
          workflows=[],  # Will add later
          activities=[],  # Will add later
      )

      await worker.run()

  if __name__ == "__main__":
      asyncio.run(main())
  ```

- [ ] **Update:** `docker-compose.yml`
  - Add temporal-worker service:
    ```yaml
    temporal-worker:
      build:
        context: ./backend
        dockerfile: Dockerfile
      command: python workers/temporal_worker.py
      environment:
        TEMPORAL_HOST: temporal:7233
        DATABASE_URL: postgresql://postgres:postgres@postgres:5432/secanalysis
      depends_on:
        - temporal
        - postgres
      volumes:
        - ./backend:/app
        - /var/run/docker.sock:/var/run/docker.sock
    ```

- [ ] Test: `docker compose up -d temporal-worker`
- [ ] Verify: Check logs `docker compose logs temporal-worker`

#### Task 1.5: Create Hello World Temporal Workflow
- [ ] **Create:** `backend/workflows/__init__.py`
- [ ] **Create:** `backend/workflows/hello_workflow.py`
  ```python
  from temporalio import workflow, activity
  from datetime import timedelta

  @activity.defn(name="say_hello")
  async def say_hello(name: str) -> str:
      return f"Hello, {name}!"

  @workflow.defn(name="HelloWorkflow")
  class HelloWorkflow:
      @workflow.run
      async def run(self, name: str) -> str:
          result = await workflow.execute_activity(
              say_hello,
              name,
              start_to_close_timeout=timedelta(seconds=10),
          )
          return result
  ```

- [ ] **Update:** `backend/workers/temporal_worker.py`
  - Import and register workflow:
    ```python
    from workflows.hello_workflow import HelloWorkflow, say_hello

    worker = Worker(
        client,
        task_queue="code-analysis",
        workflows=[HelloWorkflow],
        activities=[say_hello],
    )
    ```

- [ ] **Create:** `backend/management/commands/test_temporal.py`
  ```python
  from django.core.management.base import BaseCommand
  from temporalio.client import Client
  from workflows.hello_workflow import HelloWorkflow
  import asyncio

  class Command(BaseCommand):
      async def run_workflow(self):
          client = await Client.connect("localhost:7233")
          result = await client.execute_workflow(
              HelloWorkflow.run,
              "Temporal",
              id="hello-workflow-test",
              task_queue="code-analysis",
          )
          self.stdout.write(f"Result: {result}")

      def handle(self, *args, **options):
          asyncio.run(self.run_workflow())
  ```

- [ ] Test: `pixi run django python manage.py test_temporal`
- [ ] Verify: Check Temporal UI http://localhost:8233 for completed workflow

**Milestone 1.1:** ✅ Temporal is working, Celery is removed

### Week 2: LLM Integration

#### Task 1.6: Add LLM Dependencies
- [ ] **File:** `backend/requirements.txt`
  - Add:
    ```
    langroid==0.1.297
    anthropic==0.18.0
    openai==1.12.0
    google-generativeai==0.3.2
    ```

- [ ] **File:** `pyproject.toml`
  - Add to `[tool.pixi.pypi-dependencies]`:
    ```toml
    langroid = "==0.1.297"
    anthropic = "==0.18.0"
    openai = "==1.12.0"
    google-generativeai = "==0.3.2"
    ```

- [ ] Run: `pixi install`

#### Task 1.7: Create LLM Configuration Management
- [ ] **Update:** `backend/apps/analysis/models.py` (if not exists, create app)
  - Verify `LLMConfig` model exists (should be from current code)
  - Add helper methods:
    ```python
    class LLMConfig(models.Model):
        # ... existing fields ...

        def get_decrypted_api_key(self):
            from django.core.signing import Signer
            signer = Signer()
            return signer.unsign(self.api_key_encrypted)

        @classmethod
        def get_active_config(cls, provider: str):
            return cls.objects.filter(provider=provider, is_active=True).first()
    ```

#### Task 1.8: Create System Prompt Management
- [ ] **Create:** `backend/management/commands/load_system_prompts.py`
  ```python
  from django.core.management.base import BaseCommand
  from apps.analysis.models import SystemPrompt

  PROMPTS = {
      'triage': """You are a security triage specialist performing rapid binary classification...
      [Full prompt from REQUIREMENTS.md]
      """,
      'explainer': """You are an expert security analyst...
      [Full prompt from REQUIREMENTS.md]
      """,
      'fixer': """You are a security-focused software engineer...
      [Full prompt from REQUIREMENTS.md]
      """,
  }

  class Command(BaseCommand):
      def handle(self, *args, **options):
          for agent_type, prompt in PROMPTS.items():
              SystemPrompt.objects.update_or_create(
                  agent_type=agent_type,
                  pattern='multi_agent',
                  defaults={
                      'prompt_template': prompt,
                      'version': 1,
                      'is_active': True
                  }
              )
          self.stdout.write("System prompts loaded successfully")
  ```

- [ ] Run: `pixi run django python manage.py load_system_prompts`

#### Task 1.9: Create Basic Langroid Agent
- [ ] **Create:** `backend/agents/__init__.py`
- [ ] **Create:** `backend/agents/base_agent.py`
  ```python
  from langroid.agent.chat_agent import ChatAgent, ChatAgentConfig
  from langroid.language_models.anthropic import AnthropicConfig
  from langroid.language_models.openai_gpt import OpenAIGPTConfig
  from apps.analysis.models import LLMConfig, SystemPrompt
  import os

  class BaseSecurityAgent:
      def __init__(self, agent_type: str, provider: str = 'anthropic'):
          self.agent_type = agent_type
          self.provider = provider

          # Load system prompt
          prompt = SystemPrompt.objects.get(
              agent_type=agent_type,
              is_active=True
          ).prompt_template

          # Load LLM config
          llm_config = LLMConfig.get_active_config(provider)
          if not llm_config:
              raise ValueError(f"No active LLM config for {provider}")

          # Set API key environment variable
          if provider == 'anthropic':
              os.environ['ANTHROPIC_API_KEY'] = llm_config.get_decrypted_api_key()
              llm = AnthropicConfig(
                  chat_model="claude-sonnet-4-5-20250929",
                  chat_context_length=200000,
                  temperature=0.3
              )
          elif provider == 'openai':
              os.environ['OPENAI_API_KEY'] = llm_config.get_decrypted_api_key()
              llm = OpenAIGPTConfig(
                  chat_model="gpt-4o",
                  chat_context_length=128000,
                  temperature=0.1
              )

          self.config = ChatAgentConfig(
              name=f"{agent_type.capitalize()}Agent",
              llm=llm,
              system_message=prompt
          )
          self.agent = ChatAgent(self.config)

      async def query(self, prompt: str) -> str:
          response = await self.agent.llm_response_async(prompt)
          return response.content
  ```

- [ ] **Create:** `backend/agents/triage_agent.py`
  ```python
  from .base_agent import BaseSecurityAgent
  import json

  class TriageAgent(BaseSecurityAgent):
      def __init__(self):
          super().__init__(agent_type='triage', provider='openai')

      async def classify(self, finding: dict) -> dict:
          prompt = f"""Classify this static analysis finding as LIKELY_VULN or LIKELY_SAFE.

  Tool: {finding['tool']}
  Rule: {finding['rule_id']}
  Code:
  ```python
  {finding['code_snippet']}
  ```

  Respond with JSON ONLY:
  {{
      "classification": "LIKELY_VULN" | "LIKELY_SAFE",
      "confidence": 0.0-1.0,
      "reasoning": "one sentence"
  }}
  """
          response = await self.query(prompt)
          return json.loads(response)
  ```

#### Task 1.10: Create LLM Test Activity
- [ ] **Create:** `backend/workflows/llm_test_workflow.py`
  ```python
  from temporalio import workflow, activity
  from datetime import timedelta
  from agents.triage_agent import TriageAgent

  @activity.defn(name="test_llm_classification")
  async def test_llm_classification() -> dict:
      agent = TriageAgent()

      test_finding = {
          'tool': 'bandit',
          'rule_id': 'B105',
          'code_snippet': 'password = input("Enter password: ")'
      }

      result = await agent.classify(test_finding)
      return result

  @workflow.defn(name="LLMTestWorkflow")
  class LLMTestWorkflow:
      @workflow.run
      async def run(self) -> dict:
          result = await workflow.execute_activity(
              test_llm_classification,
              start_to_close_timeout=timedelta(seconds=30),
          )
          return result
  ```

- [ ] **Update:** `backend/workers/temporal_worker.py`
  - Register new workflow and activity

- [ ] **Create:** `backend/management/commands/test_llm.py`
  ```python
  from django.core.management.base import BaseCommand
  from temporalio.client import Client
  from workflows.llm_test_workflow import LLMTestWorkflow
  import asyncio

  class Command(BaseCommand):
      async def run_workflow(self):
          client = await Client.connect("localhost:7233")
          result = await client.execute_workflow(
              LLMTestWorkflow.run,
              id="llm-test-workflow",
              task_queue="code-analysis",
          )
          self.stdout.write(f"LLM Result: {result}")

      def handle(self, *args, **options):
          asyncio.run(self.run_workflow())
  ```

- [ ] Test: `pixi run django python manage.py test_llm`
- [ ] Verify: LLM responds with classification

**Milestone 1.2:** ✅ LLM integration working through Temporal workflow

---

## Phase 2: Static Analysis Tool Integration (Week 3)

**Goal:** Generate actual findings to feed into LLM agents

### Task 2.1: Create Static Analysis Tool Docker Images

#### Semgrep
- [ ] **Verify:** `docker pull returntocorp/semgrep:latest`
- [ ] **Update:** `docker-compose.yml`
  ```yaml
  semgrep:
    image: returntocorp/semgrep:latest
    profiles: [tools]
    volumes:
      - ./scan_temp:/src:ro
  ```

#### Bandit
- [ ] **Create:** `docker/bandit/Dockerfile`
  ```dockerfile
  FROM python:3.11-slim
  RUN pip install --no-cache-dir bandit[toml]
  WORKDIR /src
  ENTRYPOINT ["bandit"]
  ```

- [ ] Build: `docker build -t bandit:latest docker/bandit/`
- [ ] **Update:** `docker-compose.yml`
  ```yaml
  bandit:
    image: bandit:latest
    profiles: [tools]
    volumes:
      - ./scan_temp:/src:ro
  ```

#### Ruff
- [ ] **Create:** `docker/ruff/Dockerfile`
  ```dockerfile
  FROM rust:1.75-alpine as builder
  RUN cargo install ruff

  FROM alpine:latest
  COPY --from=builder /usr/local/cargo/bin/ruff /usr/local/bin/ruff
  WORKDIR /src
  ENTRYPOINT ["ruff"]
  ```

- [ ] Build: `docker build -t ruff:latest docker/ruff/`
- [ ] **Update:** `docker-compose.yml`
  ```yaml
  ruff:
    image: ruff:latest
    profiles: [tools]
    volumes:
      - ./scan_temp:/src:ro
  ```

### Task 2.2: Create Static Analysis Activities

- [ ] **Create:** `backend/workflows/activities/static_analysis.py`
  ```python
  from temporalio import activity
  import docker
  import json
  import tempfile
  import os
  from pathlib import Path

  @activity.defn(name="run_semgrep")
  async def run_semgrep(code_path: str) -> dict:
      client = docker.from_env()

      container = client.containers.run(
          "returntocorp/semgrep:latest",
          command=f"scan --json --config auto /src",
          volumes={code_path: {'bind': '/src', 'mode': 'ro'}},
          remove=True,
          detach=False
      )

      output = container.decode('utf-8')
      return {
          'tool': 'semgrep',
          'output': json.loads(output)
      }

  @activity.defn(name="run_bandit")
  async def run_bandit(code_path: str) -> dict:
      client = docker.from_env()

      container = client.containers.run(
          "bandit:latest",
          command=f"-r -f json /src",
          volumes={code_path: {'bind': '/src', 'mode': 'ro'}},
          remove=True,
          detach=False
      )

      output = container.decode('utf-8')
      return {
          'tool': 'bandit',
          'output': json.loads(output)
      }

  @activity.defn(name="run_ruff")
  async def run_ruff(code_path: str) -> dict:
      client = docker.from_env()

      container = client.containers.run(
          "ruff:latest",
          command=f"check --output-format json /src",
          volumes={code_path: {'bind': '/src', 'mode': 'ro'}},
          remove=True,
          detach=False
      )

      output = container.decode('utf-8')
      return {
          'tool': 'ruff',
          'output': json.loads(output)
      }
  ```

### Task 2.3: Create SARIF Parsing Activity

- [ ] **Create:** `backend/workflows/activities/sarif_parser.py`
  ```python
  from temporalio import activity
  from typing import List, Dict

  @activity.defn(name="parse_sarif")
  async def parse_sarif(tool_outputs: List[dict]) -> List[dict]:
      """Parse tool outputs to normalized finding format"""
      findings = []

      for output in tool_outputs:
          tool = output['tool']
          data = output['output']

          if tool == 'semgrep':
              findings.extend(parse_semgrep(data))
          elif tool == 'bandit':
              findings.extend(parse_bandit(data))
          elif tool == 'ruff':
              findings.extend(parse_ruff(data))

      return findings

  def parse_semgrep(data: dict) -> List[dict]:
      findings = []
      for result in data.get('results', []):
          findings.append({
              'tool': 'semgrep',
              'rule_id': result['check_id'],
              'severity': result['extra']['severity'],
              'file_path': result['path'],
              'start_line': result['start']['line'],
              'end_line': result['end']['line'],
              'start_column': result['start']['col'],
              'end_column': result['end']['col'],
              'code_snippet': result['extra']['lines'],
              'message': result['extra']['message'],
              'cwe_id': result['extra'].get('metadata', {}).get('cwe', ''),
              'sarif_raw': result
          })
      return findings

  def parse_bandit(data: dict) -> List[dict]:
      # Similar implementation for Bandit
      pass

  def parse_ruff(data: dict) -> List[dict]:
      # Similar implementation for Ruff
      pass
  ```

### Task 2.4: Create Storage Activity

- [ ] **Create:** `backend/workflows/activities/storage.py`
  ```python
  from temporalio import activity
  from typing import List
  from apps.scans.models import CodeScan, StaticAnalysisFinding
  from django.utils import timezone

  @activity.defn(name="store_findings")
  async def store_findings(scan_id: str, findings: List[dict]):
      scan = await CodeScan.objects.aget(id=scan_id)

      for finding in findings:
          await StaticAnalysisFinding.objects.acreate(
              scan=scan,
              tool=finding['tool'],
              rule_id=finding['rule_id'],
              severity=finding['severity'],
              file_path=finding['file_path'],
              start_line=finding['start_line'],
              end_line=finding['end_line'],
              start_column=finding.get('start_column'),
              end_column=finding.get('end_column'),
              code_snippet=finding['code_snippet'],
              message=finding['message'],
              cwe_id=finding.get('cwe_id', ''),
              sarif_raw=finding['sarif_raw']
          )

      scan.status = 'completed'
      scan.completed_at = timezone.now()
      await scan.asave()
  ```

### Task 2.5: Create Scan Workflow

- [ ] **Create:** `backend/workflows/scan_workflow.py`
  ```python
  from temporalio import workflow
  from datetime import timedelta
  from .activities.static_analysis import run_semgrep, run_bandit, run_ruff
  from .activities.sarif_parser import parse_sarif
  from .activities.storage import store_findings
  import asyncio

  @workflow.defn(name="CodeScanWorkflow")
  class CodeScanWorkflow:
      @workflow.run
      async def run(self, scan_id: str, code_path: str) -> dict:
          # Step 1: Run all tools in parallel
          semgrep_task = workflow.execute_activity(
              run_semgrep,
              code_path,
              start_to_close_timeout=timedelta(minutes=10),
          )

          bandit_task = workflow.execute_activity(
              run_bandit,
              code_path,
              start_to_close_timeout=timedelta(minutes=10),
          )

          ruff_task = workflow.execute_activity(
              run_ruff,
              code_path,
              start_to_close_timeout=timedelta(minutes=10),
          )

          tool_outputs = await asyncio.gather(
              semgrep_task,
              bandit_task,
              ruff_task
          )

          # Step 2: Parse SARIF
          findings = await workflow.execute_activity(
              parse_sarif,
              tool_outputs,
              start_to_close_timeout=timedelta(minutes=5),
          )

          # Step 3: Store in database
          await workflow.execute_activity(
              store_findings,
              args=[scan_id, findings],
              start_to_close_timeout=timedelta(minutes=5),
          )

          return {
              'scan_id': scan_id,
              'total_findings': len(findings),
              'by_tool': {
                  'semgrep': len([f for f in findings if f['tool'] == 'semgrep']),
                  'bandit': len([f for f in findings if f['tool'] == 'bandit']),
                  'ruff': len([f for f in findings if f['tool'] == 'ruff']),
              }
          }
  ```

### Task 2.6: Test End-to-End Scan

- [ ] **Create:** `examples/vulnerable_code.py`
  ```python
  # Test code with known vulnerabilities
  import os

  # Hardcoded password (should trigger Bandit)
  PASSWORD = "admin123"

  # SQL injection vulnerability (should trigger Semgrep)
  def get_user(username):
      query = f"SELECT * FROM users WHERE username = '{username}'"
      return execute_query(query)

  # Command injection (should trigger Semgrep)
  def run_command(user_input):
      os.system(f"echo {user_input}")
  ```

- [ ] **Create:** `backend/management/commands/test_scan.py`
  ```python
  from django.core.management.base import BaseCommand
  from temporalio.client import Client
  from workflows.scan_workflow import CodeScanWorkflow
  from apps.scans.models import CodeScan
  from apps.organizations.models import Organization, Repository, Branch
  import asyncio
  import uuid

  class Command(BaseCommand):
      async def run_scan(self):
          # Create scan record
          org = await Organization.objects.afirst()
          repo = await Repository.objects.afirst()

          scan = await CodeScan.objects.acreate(
              organization=org,
              repository=repo,
              scan_type='full',
              status='queued'
          )

          # Trigger workflow
          client = await Client.connect("localhost:7233")
          result = await client.execute_workflow(
              CodeScanWorkflow.run,
              args=[str(scan.id), "/app/examples"],
              id=f"code-scan-{scan.id}",
              task_queue="code-analysis",
          )

          self.stdout.write(f"Scan complete: {result}")

      def handle(self, *args, **options):
          asyncio.run(self.run_scan())
  ```

- [ ] Run: `pixi run django python manage.py test_scan`
- [ ] Verify: Check database for findings
- [ ] Verify: Check Temporal UI for workflow execution

**Milestone 2:** ✅ Can scan Python code and generate findings in database

---

## Phase 3: Agent Pattern A - Post-Processing (Week 4)

**Goal:** Implement first complete agent pattern with metrics

### Task 3.1: Create Adjudication Database Models

- [ ] **Create migration:** Add missing tables
  ```sql
  CREATE TABLE agent_interactions (
      id UUID PRIMARY KEY,
      finding_id UUID REFERENCES static_analysis_findings(id),
      agent_name VARCHAR(100),
      agent_type VARCHAR(50),
      prompt TEXT,
      response TEXT,
      tokens_used INTEGER,
      cost_usd DECIMAL(10, 6),
      latency_ms INTEGER,
      created_at TIMESTAMP
  );

  CREATE TABLE pattern_metrics (
      id UUID PRIMARY KEY,
      scan_id UUID REFERENCES code_scans(id),
      pattern VARCHAR(50),
      total_findings INTEGER,
      true_positives INTEGER,
      false_positives INTEGER,
      uncertain_count INTEGER,
      avg_confidence FLOAT,
      total_tokens_used INTEGER,
      total_cost_usd DECIMAL(10, 4),
      avg_latency_ms INTEGER,
      execution_time_seconds INTEGER
  );
  ```

- [ ] Run: `pixi run makemigrations`
- [ ] Run: `pixi run migrate`

### Task 3.2: Implement ExplainerAgent

- [ ] **Create:** `backend/agents/explainer_agent.py`
  ```python
  from .base_agent import BaseSecurityAgent
  from anthropic import Anthropic
  import json
  import os

  class ExplainerAgent(BaseSecurityAgent):
      def __init__(self):
          super().__init__(agent_type='explainer', provider='anthropic')
          self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

      async def explain(self, finding: dict) -> dict:
          prompt = f"""Provide detailed vulnerability analysis.

  Finding:
  - Tool: {finding['tool']}
  - Rule: {finding['rule_id']}
  - Location: {finding['file_path']}:{finding['start_line']}

  Code:
  ```python
  {finding['code_snippet']}
  ```

  Message: {finding['message']}

  Analyze step-by-step:
  1. Identify input sources
  2. Trace data flow
  3. Check sanitization
  4. Assess exploitability

  Respond with JSON:
  {{
      "verdict": "TRUE_POSITIVE|FALSE_POSITIVE|UNCERTAIN",
      "confidence": 0.0-1.0,
      "trace": ["step 1", "step 2", ...],
      "cwe_id": "CWE-XXX",
      "reasoning": "detailed explanation"
  }}
  """

          message = self.client.messages.create(
              model="claude-sonnet-4-5-20250929",
              max_tokens=4000,
              messages=[{"role": "user", "content": prompt}]
          )

          return json.loads(message.content[0].text)
  ```

### Task 3.3: Create Post-Processing Activity

- [ ] **Create:** `backend/workflows/activities/adjudication.py`
  ```python
  from temporalio import activity
  from agents.explainer_agent import ExplainerAgent
  from apps.findings.models import LLMAdjudication
  from apps.analysis.models import AgentInteraction
  from django.utils import timezone
  import time

  @activity.defn(name="adjudicate_finding_post_processing")
  async def adjudicate_finding_post_processing(finding: dict) -> dict:
      agent = ExplainerAgent()

      start_time = time.time()
      result = await agent.explain(finding)
      latency_ms = int((time.time() - start_time) * 1000)

      # Store adjudication
      adjudication = await LLMAdjudication.objects.acreate(
          finding_id=finding['id'],
          agent_pattern='post_processing',
          llm_provider='anthropic',
          model_name='claude-sonnet-4-5-20250929',
          verdict=result['verdict'],
          confidence=result['confidence'],
          reasoning=result['reasoning'],
          trace=result.get('trace', []),
          tokens_used=result.get('tokens_used', 0),
          latency_ms=latency_ms
      )

      # Store interaction log
      await AgentInteraction.objects.acreate(
          finding_id=finding['id'],
          agent_name='ExplainerAgent',
          agent_type='explainer',
          prompt=f"Analyze finding {finding['rule_id']}",
          response=result['reasoning'],
          tokens_used=result.get('tokens_used', 0),
          cost_usd=calculate_cost(result.get('tokens_used', 0), 'claude'),
          latency_ms=latency_ms
      )

      return result

  def calculate_cost(tokens: int, model: str) -> float:
      # Claude Sonnet 4.5: $3/MTok input, $15/MTok output
      # Simplified: assume 50/50 split
      input_tokens = tokens // 2
      output_tokens = tokens // 2
      return (input_tokens * 3 + output_tokens * 15) / 1_000_000
  ```

### Task 3.4: Create Post-Processing Workflow

- [ ] **Create:** `backend/workflows/adjudication_workflows.py`
  ```python
  from temporalio import workflow
  from datetime import timedelta
  from .activities.adjudication import adjudicate_finding_post_processing
  from typing import List

  @workflow.defn(name="PostProcessingAdjudication")
  class PostProcessingAdjudication:
      @workflow.run
      async def run(self, scan_id: str, findings: List[dict]) -> dict:
          results = []

          for finding in findings:
              result = await workflow.execute_activity(
                  adjudicate_finding_post_processing,
                  finding,
                  start_to_close_timeout=timedelta(minutes=2),
              )
              results.append(result)

          # Calculate metrics
          true_positives = len([r for r in results if r['verdict'] == 'TRUE_POSITIVE'])
          false_positives = len([r for r in results if r['verdict'] == 'FALSE_POSITIVE'])
          uncertain = len([r for r in results if r['verdict'] == 'UNCERTAIN'])

          avg_confidence = sum(r['confidence'] for r in results) / len(results)
          total_tokens = sum(r.get('tokens_used', 0) for r in results)
          total_cost = sum(calculate_cost(r.get('tokens_used', 0), 'claude') for r in results)

          # Store metrics
          await workflow.execute_activity(
              store_pattern_metrics,
              args=[scan_id, 'post_processing', {
                  'total_findings': len(findings),
                  'true_positives': true_positives,
                  'false_positives': false_positives,
                  'uncertain_count': uncertain,
                  'avg_confidence': avg_confidence,
                  'total_tokens_used': total_tokens,
                  'total_cost_usd': total_cost,
              }],
              start_to_close_timeout=timedelta(minutes=1),
          )

          return {
              'pattern': 'post_processing',
              'total_findings': len(findings),
              'true_positives': true_positives,
              'false_positives': false_positives,
              'uncertain': uncertain,
              'avg_confidence': avg_confidence,
              'total_cost_usd': total_cost
          }
  ```

### Task 3.5: Integrate with Main Scan Workflow

- [ ] **Update:** `backend/workflows/scan_workflow.py`
  - After storing findings, trigger adjudication:
    ```python
    # Step 4: Run adjudication (Pattern A)
    adjudication_result = await workflow.execute_child_workflow(
        PostProcessingAdjudication.run,
        args=[scan_id, findings],
        id=f"adjudication-{scan_id}",
    )

    return {
        'scan_id': scan_id,
        'total_findings': len(findings),
        'adjudication': adjudication_result
    }
    ```

### Task 3.6: Test Complete Pipeline

- [ ] Run: `pixi run django python manage.py test_scan`
- [ ] Verify: Findings are adjudicated by LLM
- [ ] Verify: Metrics are stored
- [ ] Check Temporal UI: See both scan and adjudication workflows

**Milestone 3:** ✅ Can scan code, adjudicate with LLM, and store metrics

---

## Phase 4: Deduplication System (Week 5)

[Continue with similar detailed breakdown for Phases 4-9...]

**Due to length constraints, I'll summarize remaining phases:**

### Phase 4: Deduplication (Week 5)
- Deploy Qdrant
- Implement exact matching
- Build Rust embedding service
- Implement semantic clustering
- Create LLM confirmation workflow

### Phase 5: Agent Patterns B & C (Weeks 6-7)
- Implement Interactive Retrieval pattern
- Build Rust parser service with tree-sitter
- Implement Multi-Agent pattern (Triage → Explainer → Fixer)
- Create FixerAgent with code suggestions
- Run comparative analysis

### Phase 6: Rust Parser Service (Week 8)
- Set up Rust project with Actix-web
- Implement tree-sitter parsing
- Create `/parse` endpoint
- Create `/embeddings` endpoint
- Integrate with Interactive agent

### Phase 7: Frontend (Weeks 9-11)
- Initialize React + TypeScript project
- Implement findings dashboard
- Integrate ReactFlow for DAG visualization
- Create Monaco code editor
- Build chat interface
- Create pattern comparison view

### Phase 8: RAG System (Week 12)
- Implement document upload
- Generate embeddings for requirements
- Store in Qdrant
- Build retrieval system
- Integrate with agent prompts

### Phase 9: Testing & Polish (Week 13)
- End-to-end integration tests
- Performance benchmarking
- Optimize workflows
- Create demo script
- Write final documentation

---

## Progress Tracking

Update this section as you complete tasks:

**Current Phase:** Phase 1 - Foundation
**Completion:** 0/13 weeks
**Blockers:** None
**Next Milestone:** Temporal integration + LLM proof-of-concept

---

## Quick Reference Commands

```bash
# Development
pixi run runserver          # Django dev server
pixi run temporal-worker    # Start Temporal worker
pixi run migrate            # Run migrations
pixi run makemigrations     # Create migrations

# Testing
pixi run test               # Run pytest
pixi run test_scan          # Test complete scan pipeline
pixi run test_llm           # Test LLM integration

# Docker
docker compose up -d        # Start all services
docker compose logs -f temporal  # View Temporal logs
docker compose restart temporal-worker  # Restart worker

# Temporal UI
open http://localhost:8233  # View workflow executions

# Database
pixi run shell              # Django shell for queries
```

---

## Notes

- Keep ADRs updated as implementation progresses
- Document any deviations from this roadmap
- Track actual vs estimated effort for future planning
- Prioritize working end-to-end over perfect components
