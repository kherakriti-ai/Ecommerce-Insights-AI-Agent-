CREATE DATABASE IF NOT EXISTS SNOWFLAKE_INTELLIGENCE;
CREATE SCHEMA IF NOT EXISTS SNOWFLAKE_INTELLIGENCE.AGENTS;

USE DATABASE SNOWFLAKE_INTELLIGENCE;
USE SCHEMA AGENTS;

CREATE OR REPLACE AGENT SNOWFLAKE_INTELLIGENCE.AGENTS.ECOMMERCE_AGENT
  COMMENT = 'AI agent for ecommerce analytics across sales, customer behavior, and operations'
  PROFILE = '{"display_name": "Ecommerce Insights Agent", "color": "blue"}'
  FROM SPECIFICATION
$$
models:
  orchestration: claude-4-sonnet

orchestration:
  budget:
    seconds: 30
    tokens: 16000

instructions:
  response: "Keep responses concise, clear, and business-friendly."
  orchestration: "Use Analyst for structured ecommerce questions about revenue, customer behavior, product performance, device usage, discounts, ratings, and delivery performance."
  system: "You are an ecommerce analytics assistant helping users answer business questions from structured ecommerce data."
  sample_questions:
    - question: "Which product category generates the highest revenue?"
      answer: "I'll analyze the ecommerce data by product category revenue."
    - question: "Do returning customers spend more than new customers?"
      answer: "I'll compare spending between returning and new customers."

tools:
  - tool_spec:
      type: "cortex_analyst_text_to_sql"
      name: "Analyst"
      description: "Query structured ecommerce data for metrics, trends, comparisons, and aggregations."

tool_resources:
  Analyst:
    semantic_view: "ECOMMERCE.RETAIL.ECOMMERCE_SEMANTIC_VIEW"
    warehouse: "COMPUTE_WH"
    timeout_seconds: 30
$$;
