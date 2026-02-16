# System Design Document: Circle K-style Convenience Store POS System
## Offline-First Store Edge Architecture with Real-Time HQ Synchronization

**Document Version:** 1.0  
**Date:** February 16, 2026  
**Author:** System Design Practice  
**Status:** Draft for Learning & Implementation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Requirements Document (SRD)](#2-system-requirements-document-srd)
   - 2.1 [Business Context](#21-business-context)
   - 2.2 [Functional Requirements](#22-functional-requirements)
   - 2.3 [Non-Functional Requirements](#23-non-functional-requirements)
   - 2.4 [Quality Attributes](#24-quality-attributes)
3. [System Architecture](#3-system-architecture)
   - 3.1 [Architectural Principles](#31-architectural-principles)
   - 3.2 [High-Level Architecture](#32-high-level-architecture)
   - 3.3 [Component Architecture](#33-component-architecture)
4. [Store Edge Layer Design](#4-store-edge-layer-design)
   - 4.1 [Store Edge Components](#41-store-edge-components)
   - 4.2 [Database Schema](#42-database-schema)
   - 4.3 [Offline-First Strategy](#43-offline-first-strategy)
5. [HQ Platform Layer Design](#5-hq-platform-layer-design)
   - 5.1 [HQ Services](#51-hq-services)
   - 5.2 [Data Ingestion Pipeline](#52-data-ingestion-pipeline)
6. [Synchronization Design](#6-synchronization-design)
   - 6.1 [Outbox Pattern Implementation](#61-outbox-pattern-implementation)
   - 6.2 [Event Types & Schema](#62-event-types--schema)
   - 6.3 [Conflict Resolution Strategy](#63-conflict-resolution-strategy)
   - 6.4 [Network Partition Handling](#64-network-partition-handling)
7. [API Design](#7-api-design)
   - 7.1 [Store Edge APIs](#71-store-edge-apis)
   - 7.2 [HQ Platform APIs](#72-hq-platform-apis)
   - 7.3 [Sync Protocol](#73-sync-protocol)
8. [Technology Stack](#8-technology-stack)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Security Design](#10-security-design)
11. [Monitoring & Observability](#11-monitoring--observability)
12. [Testing Strategy](#12-testing-strategy)
13. [Implementation Roadmap](#13-implementation-roadmap)
14. [Appendix](#14-appendix)

---

## 1. Executive Summary

This document describes the system design for a **Circle K-style convenience store POS system** with emphasis on **offline-first architecture** and **real-time headquarters synchronization**. The system supports a chain of 24/7 convenience stores, each operating 5 POS terminals with QR-based payment processing.

### Key Design Goals
- **High Availability**: Each store operates independently during WAN outages
- **Real-Time Sync**: Near-instant transaction synchronization when connected
- **Data Consistency**: Guaranteed delivery of transactions with conflict resolution
- **Scalability**: Support 100+ stores with 500+ concurrent POS terminals
- **Operational Excellence**: Centralized monitoring and management of distributed edge infrastructure

### Core Architecture Pattern
**Store Edge + HQ Platform** with transactional outbox pattern for reliable messaging, event-driven synchronization, and offline-first data model.

---

## 2. System Requirements Document (SRD)

### 2.1 Business Context

**Domain**: Retail convenience store chain (similar to Circle K Vietnam)

**Business Model**:
- 24/7 operation across multiple store locations
- Fast checkout experience (<2 minutes per transaction)
- Real-time inventory visibility for replenishment
- Centralized pricing and promotion management
- Customer loyalty program integration

**Stakeholders**:
- Store Cashiers: Primary POS users
- Store Managers: Inventory and daily reporting
- HQ Operations: Fleet management, analytics
- Finance Team: Payment reconciliation
- IT Operations: System monitoring and maintenance

**Success Metrics**:
- POS uptime: 99.9% (including offline mode)
- Average transaction time: <90 seconds
- Sync latency: <5 seconds (when online)
- Data loss: Zero transactions lost
- Store autonomy: Full operation during WAN outage

---

### 2.2 Functional Requirements

#### FR-1: Point of Sale (POS) Operations

**FR-1.1 Transaction Creation**
- System SHALL allow cashiers to create new transactions with unique transaction IDs
- System SHALL support scanning barcodes to add items to transaction
- System SHALL display real-time running total including taxes and discounts
- System SHALL prevent duplicate item scans within configurable time window (3 seconds)

**FR-1.2 Item Management**
- System SHALL retrieve item details (name, price, tax category) from local catalog
- System SHALL support manual quantity adjustment
- System SHALL support line item removal before payment
- System SHALL validate item availability in local inventory

**FR-1.3 Payment Processing**
- System SHALL generate QR codes for payment using configured payment provider
- System SHALL poll payment status with timeout (60 seconds)
- System SHALL mark transactions as PAID upon successful payment confirmation
- System SHALL support payment cancellation and transaction voiding
- System SHALL record payment method, amount, and provider reference

**FR-1.4 Receipt Generation**
- System SHALL generate digital receipts with transaction details
- System SHALL include store info, items, totals, payment method, timestamp
- System SHALL support receipt reprint for past transactions (same day)

**FR-1.5 Transaction States**
- Supported states: DRAFT, PENDING_PAYMENT, PAID, VOID, REFUND_REQUESTED, REFUNDED
- State transitions SHALL be validated and logged

#### FR-2: Inventory Management

**FR-2.1 Stock Level Tracking**
- System SHALL maintain current stock levels per SKU per store
- System SHALL decrement stock upon transaction completion (PAID state)
- System SHALL support manual stock adjustments with reason codes
- System SHALL record stock movement history

**FR-2.2 Stock Replenishment**
- System SHALL support receiving shipments and updating stock levels
- System SHALL generate low-stock alerts based on configurable thresholds
- System SHALL record supplier information and receiving timestamps

**FR-2.3 Inventory Reconciliation**
- System SHALL support daily stock count (physical inventory)
- System SHALL calculate and record shrinkage (system vs physical difference)
- System SHALL flag discrepancies exceeding threshold (5%) for review

#### FR-3: Catalog & Pricing

**FR-3.1 Product Catalog**
- System SHALL maintain master product catalog with SKU, barcode, name, category, tax rate
- System SHALL support multiple barcodes per SKU
- System SHALL synchronize catalog updates from HQ to stores

**FR-3.2 Pricing Management**
- System SHALL support store-specific pricing overrides
- System SHALL support scheduled price changes (effective date/time)
- System SHALL apply correct price based on transaction timestamp

**FR-3.3 Promotions**
- System SHALL apply eligible promotions automatically during checkout
- System SHALL support promotion types: percentage discount, fixed amount discount, buy-X-get-Y
- System SHALL validate promotion eligibility (date range, minimum purchase, eligible SKUs)
- System SHALL display applied promotions on receipt

#### FR-4: Offline Operations

**FR-4.1 Offline Mode Detection**
- System SHALL detect HQ connectivity loss automatically
- System SHALL switch to offline mode within 5 seconds of detection
- System SHALL display offline status indicator on POS UI

**FR-4.2 Offline Transaction Handling**
- System SHALL continue processing transactions using local database during offline mode
- System SHALL queue all events for synchronization in outbox table
- System SHALL prevent operations requiring online validation (e.g., gift card activation)

**FR-4.3 Offline Data Freshness**
- System SHALL use last synchronized catalog/pricing data during offline mode
- System SHALL display data staleness indicator (last sync timestamp)
- System SHALL limit offline operation duration to 24 hours before requiring manual intervention

#### FR-5: Synchronization

**FR-5.1 Store to HQ Sync**
- System SHALL transmit transaction events to HQ in real-time when online
- System SHALL guarantee exactly-once semantic for transaction delivery using idempotency keys
- System SHALL retry failed transmissions with exponential backoff (max 5 minutes)
- System SHALL preserve event ordering per store

**FR-5.2 HQ to Store Sync**
- System SHALL pull catalog/pricing/promotion updates from HQ every 15 minutes
- System SHALL apply updates transactionally to avoid partial state
- System SHALL support emergency push updates (price corrections)

**FR-5.3 Conflict Resolution**
- System SHALL detect conflicts (e.g., concurrent stock adjustments)
- System SHALL resolve conflicts using "HQ wins" strategy for master data
- System SHALL log all conflicts for audit and manual review

#### FR-6: User Management

**FR-6.1 Authentication**
- System SHALL require cashier login with employee ID and PIN
- System SHALL enforce single active session per cashier per terminal
- System SHALL support shift change without system restart

**FR-6.2 Authorization**
- System SHALL enforce role-based permissions (Cashier, Manager, Admin)
- System SHALL restrict sensitive operations (refunds, voids) to Manager role
- System SHALL log all authorization decisions

#### FR-7: Reporting

**FR-7.1 Store Reports**
- System SHALL generate end-of-day sales summary (total sales, payment breakdown, transaction count)
- System SHALL generate current inventory snapshot
- System SHALL generate cashier performance report (transactions per hour, average transaction value)

**FR-7.2 HQ Reports**
- System SHALL aggregate sales across all stores (daily, weekly, monthly)
- System SHALL generate inventory turnover reports
- System SHALL generate payment reconciliation reports per payment provider
- System SHALL support custom date range queries

---

### 2.3 Non-Functional Requirements

#### NFR-1: Performance

**NFR-1.1 Response Time**
- Transaction creation API SHALL respond within 200ms (p95)
- Item lookup by barcode SHALL complete within 100ms (p95)
- Payment QR generation SHALL complete within 500ms (p95)
- Store report generation SHALL complete within 3 seconds (p95)

**NFR-1.2 Throughput**
- Each store edge SHALL support 5 concurrent POS terminals
- Each POS terminal SHALL handle 20 transactions per hour (peak)
- HQ ingestion pipeline SHALL process 10,000 events per minute

**NFR-1.3 Sync Latency**
- Event transmission from store to HQ SHALL complete within 5 seconds (p95) when online
- Catalog updates SHALL propagate to stores within 15 minutes

#### NFR-2: Availability

**NFR-2.1 Store Edge Uptime**
- Store edge services SHALL achieve 99.9% uptime (including offline mode)
- Store edge SHALL operate continuously during HQ maintenance windows

**NFR-2.2 HQ Platform Uptime**
- HQ platform SHALL achieve 99.5% uptime
- HQ downtime SHALL NOT impact store operations (offline mode)

**NFR-2.3 Recovery Time**
- Store edge SHALL recover from crash within 60 seconds
- Store edge SHALL resume synchronization automatically upon connectivity restoration

#### NFR-3: Scalability

**NFR-3.1 Horizontal Scaling**
- Architecture SHALL support 1,000 stores without redesign
- HQ ingestion layer SHALL scale horizontally by adding consumer instances
- Store edge SHALL NOT be bottlenecked by single-threaded components

**NFR-3.2 Data Volume**
- System SHALL handle 100,000 transactions per day across all stores
- System SHALL retain 2 years of transaction history
- Database growth SHALL be monitored and archived periodically

#### NFR-4: Reliability

**NFR-4.1 Data Durability**
- Transaction data SHALL be persisted to disk before acknowledging to POS
- Store database SHALL use WAL (write-ahead logging) for crash recovery
- HQ SHALL replicate data across multiple availability zones

**NFR-4.2 Fault Tolerance**
- System SHALL tolerate network partitions without data loss
- System SHALL tolerate store edge hardware failures (restore from backup)
- System SHALL tolerate message broker failures (retry from outbox)

**NFR-4.3 Exactly-Once Semantics**
- Transaction events SHALL be delivered exactly once to HQ (deduplication via idempotency)
- Inventory adjustments SHALL be applied idempotently

#### NFR-5: Security

**NFR-5.1 Authentication & Authorization**
- All API calls SHALL require valid JWT tokens
- JWT tokens SHALL expire after 8 hours
- Sensitive operations SHALL require additional authorization checks

**NFR-5.2 Data Encryption**
- Data in transit SHALL be encrypted using TLS 1.3
- Sensitive data at rest (payment provider secrets) SHALL be encrypted using AES-256
- Database connections SHALL use SSL/TLS

**NFR-5.3 Audit Logging**
- All state-changing operations SHALL be logged with timestamp, user, and outcome
- Audit logs SHALL be immutable and retained for 7 years
- Access to audit logs SHALL be restricted to compliance team

**NFR-5.4 Payment Security**
- System SHALL NOT store credit card numbers or CVV
- Payment processing SHALL comply with PCI DSS requirements (QR payments reduce scope)
- Payment provider credentials SHALL be rotated quarterly

#### NFR-6: Maintainability

**NFR-6.1 Observability**
- All services SHALL emit structured logs (JSON format)
- All critical paths SHALL be instrumented with metrics (latency, throughput, error rate)
- All services SHALL support distributed tracing (trace ID propagation)

**NFR-6.2 Deployment**
- Store edge SHALL support zero-downtime updates (blue-green deployment)
- HQ services SHALL deploy independently without coordination
- Configuration changes SHALL NOT require code redeployment

**NFR-6.3 Debuggability**
- Event logs SHALL include full context (store_id, terminal_id, transaction_id, cashier_id)
- Database queries SHALL be logged with execution time
- System SHALL support replay of events for debugging

#### NFR-7: Usability

**NFR-7.1 POS UI Responsiveness**
- POS interface SHALL provide visual feedback within 100ms of user action
- Barcode scan SHALL trigger UI update within 200ms
- Offline mode indicator SHALL be prominently displayed

**NFR-7.2 Error Handling**
- System SHALL display user-friendly error messages (no stack traces)
- System SHALL suggest corrective actions for common errors
- Critical errors SHALL alert store manager automatically

---

### 2.4 Quality Attributes

| Quality Attribute | Scenario | Response Measure |
|------------------|----------|------------------|
| **Availability** | Store loses WAN connectivity during peak hours | Store continues processing transactions with <1 second disruption; all transactions synced within 5 seconds of reconnection |
| **Performance** | Cashier scans 10 items and completes payment during rush hour | Total checkout completes in <90 seconds; each barcode scan responds in <200ms |
| **Reliability** | Store edge server crashes mid-transaction | System recovers within 60 seconds; no transaction data lost; transaction either completes or rolls back cleanly |
| **Consistency** | HQ updates price while store is offline | Store applies old price during offline period; price correction mechanism triggered upon sync; no transaction data loss |
| **Security** | Unauthorized user attempts to access admin functions | Access denied; attempt logged in audit trail; security alert triggered after 3 failed attempts |
| **Scalability** | Chain expands from 100 to 500 stores | HQ ingestion scales horizontally; no degradation in sync latency; store edge unchanged |
| **Maintainability** | Critical bug requires hotfix deployment | Hotfix deployed to store edge within 2 hours; zero-downtime rolling update; rollback capability within 5 minutes |
| **Testability** | Engineer debugging sync failure for specific store | Trace ID allows full request path reconstruction; event replay possible from outbox; logs contain full context |

---

## 3. System Architecture

### 3.1 Architectural Principles

1. **Offline-First by Default**
   - Store operations MUST NOT depend on HQ availability
   - Every write operation stores data locally before attempting network calls
   - Network is treated as enhancement, not requirement

2. **Event-Driven Communication**
   - State changes published as events (SaleRecorded, InventoryAdjusted)
   - Components communicate asynchronously via message broker
   - Loose coupling enables independent scaling and deployment

3. **Transactional Outbox for Reliability**
   - Business logic writes to database and outbox in single transaction
   - Separate relay process publishes events from outbox
   - Eliminates dual-write problem and guarantees message delivery

4. **Idempotent Consumers**
   - All event consumers MUST handle duplicate events safely
   - Use event_id/transaction_id for deduplication
   - "At-least-once delivery" + idempotency = exactly-once semantics

5. **HQ as Central Brain, Stores as Autonomous Agents**
   - HQ distributes master data (catalog, pricing, promotions)
   - Stores operate independently with local decision-making
   - HQ aggregates data for analytics and reporting

6. **Immutable Event Logs**
   - Events are append-only (never updated or deleted)
   - Source of truth for transaction history
   - Enables audit trails and event replay

---

### 3.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         HQ Platform (Cloud)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Catalog    │  │   Pricing    │  │  Promotion   │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Transaction │  │  Inventory   │  │   Loyalty    │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────┐       │
│  │         Message Broker (Kafka/Redpanda)          │       │
│  │  Topics: transactions, inventory, catalog-updates│       │
│  └──────────────────────────────────────────────────┘       │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Analytics   │  │   Reporting  │  │   Identity   │      │
│  │     DB       │  │   Service    │  │   Service    │      │
│  │ (Clickhouse) │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ gRPC Stream / HTTPS
                              │ (Event Upload + Master Data Pull)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Store Edge (Each Store)                   │
│                                                               │
│  ┌──────────────────────────────────────────────────┐       │
│  │            Store Edge Server (Docker)             │       │
│  │                                                    │       │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │       │
│  │  │  Checkout   │  │   Catalog   │  │   Sync   │ │       │
│  │  │  API        │  │   API       │  │  Agent   │ │       │
│  │  └─────────────┘  └─────────────┘  └──────────┘ │       │
│  │                                                    │       │
│  │  ┌───────────────────────────────────────────┐   │       │
│  │  │         Store Database (Postgres)         │   │       │
│  │  │  - transactions                           │   │       │
│  │  │  - line_items                             │   │       │
│  │  │  - payments                               │   │       │
│  │  │  - local_inventory                        │   │       │
│  │  │  - local_catalog (snapshot)               │   │       │
│  │  │  - outbox (events to sync)                │   │       │
│  │  │  - inbox (deduplication)                  │   │       │
│  │  └───────────────────────────────────────────┘   │       │
│  │                                                    │       │
│  │  ┌─────────────┐                                  │       │
│  │  │   Outbox    │  (polls outbox, publishes        │       │
│  │  │   Relay     │   events to HQ)                  │       │
│  │  └─────────────┘                                  │       │
│  └──────────────────────────────────────────────────┘       │
│                                                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ POS #1  │  │ POS #2  │  │ POS #3  │  │ POS #4  │ ...    │
│  │Terminal │  │Terminal │  │Terminal │  │Terminal │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                               │
│  ┌──────────────────────┐                                    │
│  │  Payment Gateway     │                                    │
│  │  (QR Code Provider)  │                                    │
│  └──────────────────────┘                                    │
└─────────────────────────────────────────────────────────────┘
```

---

### 3.3 Component Architecture

#### Store Edge Components

1. **Checkout API**
   - REST API for POS operations (create transaction, add items, finalize payment)
   - Validates business rules (item availability, pricing)
   - Writes to local Postgres in ACID transactions
   - Inserts events into outbox table within same transaction

2. **Catalog API**
   - Serves product catalog and pricing to POS terminals
   - Reads from local snapshot (synchronized from HQ)
   - Fast lookups by barcode (indexed)

3. **Sync Agent**
   - Background process running continuously
   - **Upstream sync**: Polls outbox table, publishes events to HQ via gRPC stream
   - **Downstream sync**: Pulls master data packages from HQ, applies to local DB
   - Implements exponential backoff retry logic

4. **Outbox Relay**
   - Separate process (can be embedded or standalone)
   - Polls outbox table using `SELECT ... FOR UPDATE SKIP LOCKED`
   - Publishes events to message broker or HQ ingestion endpoint
   - Marks events as published after receiving acknowledgment

5. **Store Database (Postgres)**
   - Single source of truth for store operations
   - ACID compliance ensures data consistency
   - Write-Ahead Logging (WAL) for crash recovery

#### HQ Platform Components

1. **Transaction Service**
   - Receives transaction events from all stores
   - Writes to central transaction database (append-only)
   - Publishes events to message broker for downstream consumers
   - Implements idempotency using inbox pattern (deduplication by event_id)

2. **Catalog Service**
   - Manages master product catalog
   - Versions catalog changes (version number incremented on update)
   - Generates delta packages for efficient store synchronization

3. **Pricing Service**
   - Manages base prices and store-specific overrides
   - Supports scheduled price changes
   - Generates pricing snapshots for store distribution

4. **Promotion Service**
   - Configures promotion rules and eligibility
   - Generates promotion packages for store distribution
   - Tracks promotion effectiveness

5. **Inventory Service**
   - Aggregates inventory levels across all stores
   - Receives inventory adjustment events from stores
   - Generates replenishment recommendations

6. **Reporting Service**
   - Queries analytics database (Clickhouse) for aggregated reports
   - Serves dashboards and custom queries
   - Pre-computes common aggregations (daily sales, top SKUs)

7. **Identity Service**
   - Issues JWT tokens for authentication
   - Manages users, roles, and permissions
   - Handles device registration for POS terminals

8. **Message Broker (Kafka/Redpanda)**
   - Central nervous system for event distribution
   - Topics: `transactions`, `inventory-adjustments`, `catalog-updates`
   - Guarantees ordering within partition (partition by store_id)

---

## 4. Store Edge Layer Design

### 4.1 Store Edge Components

Each store runs a **containerized edge server** (Docker or k3s) on dedicated hardware:
- Mini PC / Edge gateway (8GB RAM, 256GB SSD minimum)
- Runs Linux (Ubuntu Server or Alpine)
- Local network (LAN) connects 5 POS terminals to edge server
- WAN connection to HQ (4G/5G backup if fiber fails)

**Edge Server Stack**:
```
┌──────────────────────────────┐
│   Checkout API (FastAPI)     │
│   Catalog API (FastAPI)      │
│   Sync Agent (Python)        │
│   Outbox Relay (Python)      │
├──────────────────────────────┤
│   Postgres 15                │
│   (with Outbox/Inbox tables) │
├──────────────────────────────┤
│   NGINX (Reverse Proxy)      │
│   Health Check Endpoint      │
└──────────────────────────────┘
```

---

### 4.2 Database Schema

#### Core Tables

**transactions**
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id VARCHAR(50) NOT NULL,
    terminal_id VARCHAR(50) NOT NULL,
    cashier_id VARCHAR(50),
    
    status VARCHAR(20) NOT NULL 
        CHECK (status IN ('DRAFT', 'PENDING_PAYMENT', 'PAID', 'VOID', 'REFUNDED')),
    
    subtotal DECIMAL(10,2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    
    payment_method VARCHAR(50),  -- 'QR_VNPAY', 'QR_MOMO', 'CASH'
    payment_provider_ref VARCHAR(255),
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    -- Offline metadata
    local_sequence BIGSERIAL,  -- monotonic counter for ordering
    synced_at TIMESTAMPTZ,     -- when event was successfully sent to HQ
    sync_attempts INT DEFAULT 0
);

CREATE INDEX idx_txn_store_created ON transactions(store_id, created_at);
CREATE INDEX idx_txn_status ON transactions(status);
CREATE INDEX idx_txn_local_sequence ON transactions(local_sequence);
```

**line_items**
```sql
CREATE TABLE line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    
    sku_id VARCHAR(50) NOT NULL,
    barcode VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL,
    line_subtotal DECIMAL(10,2) NOT NULL,
    line_discount DECIMAL(10,2) NOT NULL DEFAULT 0,
    line_total DECIMAL(10,2) NOT NULL,
    
    applied_promotions JSONB,  -- array of {promo_id, discount_amount}
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_line_items_txn ON line_items(transaction_id);
```

**payments**
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id),
    
    payment_method VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL 
        CHECK (status IN ('PENDING', 'CAPTURED', 'FAILED', 'REFUNDED')),
    
    provider VARCHAR(50),  -- 'VNPAY', 'MOMO'
    provider_txn_id VARCHAR(255),
    qr_code_data TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    captured_at TIMESTAMPTZ,
    failed_reason TEXT
);

CREATE INDEX idx_payments_txn ON payments(transaction_id);
```

**local_inventory**
```sql
CREATE TABLE local_inventory (
    sku_id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(50) NOT NULL,
    
    current_stock INT NOT NULL DEFAULT 0,
    reserved_stock INT NOT NULL DEFAULT 0,  -- items in DRAFT transactions
    available_stock INT GENERATED ALWAYS AS (current_stock - reserved_stock) STORED,
    
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sync_version BIGINT  -- version from HQ
);

CREATE INDEX idx_inventory_store ON local_inventory(store_id);
```

**local_catalog** (snapshot from HQ)
```sql
CREATE TABLE local_catalog (
    sku_id VARCHAR(50) PRIMARY KEY,
    barcode VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    
    base_price DECIMAL(10,2) NOT NULL,
    tax_rate DECIMAL(5,4) NOT NULL,
    
    is_active BOOLEAN DEFAULT TRUE,
    
    catalog_version BIGINT NOT NULL,  -- version from HQ
    synced_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_catalog_barcode ON local_catalog(barcode);
CREATE INDEX idx_catalog_version ON local_catalog(catalog_version);
```

#### Synchronization Tables

**outbox** (Transactional Outbox Pattern)
```sql
CREATE TABLE outbox (
    id BIGSERIAL PRIMARY KEY,
    
    event_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,  -- 'SaleRecorded', 'InventoryAdjusted'
    aggregate_type VARCHAR(50) NOT NULL,  -- 'Transaction', 'Inventory'
    aggregate_id VARCHAR(100) NOT NULL,
    
    payload JSONB NOT NULL,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    publish_attempts INT DEFAULT 0,
    last_error TEXT
);

CREATE INDEX idx_outbox_unpublished ON outbox(created_at) 
    WHERE published_at IS NULL;
CREATE INDEX idx_outbox_event_id ON outbox(event_id);
```

**inbox** (Idempotency / Deduplication for incoming events from HQ)
```sql
CREATE TABLE inbox (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_inbox_received ON inbox(received_at);
```

**sync_cursors** (Track sync state)
```sql
CREATE TABLE sync_cursors (
    cursor_name VARCHAR(100) PRIMARY KEY,  -- 'catalog_version', 'pricing_version'
    cursor_value BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### 4.3 Offline-First Strategy

#### Detection & Transition

**Health Check Mechanism**:
- Sync Agent pings HQ health endpoint every 10 seconds
- If 3 consecutive pings fail → transition to OFFLINE mode
- Set `system_status.is_online = false` in memory

**Offline Mode Behavior**:
1. **Transactions continue normally**: Write to local DB
2. **Outbox accumulates events**: Events not sent, but persisted
3. **Catalog reads from snapshot**: Use last synced `local_catalog`
4. **Payment restrictions**: Only allow methods that work offline (future: none for QR)

#### Data Staleness Management

- Display "Last Synced: 10 minutes ago" on POS UI
- Alert store manager if offline > 2 hours
- Block new transactions if offline > 24 hours (manual override required)

#### Reconnection & Catch-Up

When connectivity restored:
1. Sync Agent detects successful ping
2. Outbox Relay resumes publishing from oldest unpublished event
3. Sync Agent pulls latest master data versions
4. System transitions back to ONLINE mode

**Catch-up Performance**:
- If 100 transactions queued → publish in batches of 50
- gRPC stream allows pipelining for faster upload
- Typical catch-up time: ~30 seconds for 100 transactions

---

## 5. HQ Platform Layer Design

### 5.1 HQ Services

#### Transaction Service

**Responsibilities**:
- Receive transaction events from stores
- Deduplicate using inbox pattern
- Persist to central transaction database
- Publish to message broker for downstream processing

**API**:
```
POST /v1/ingestion/events
Content-Type: application/json
Authorization: Bearer <store_jwt_token>

{
  "events": [
    {
      "event_id": "uuid",
      "event_type": "SaleRecorded",
      "store_id": "STORE_001",
      "timestamp": "2026-02-16T11:00:00Z",
      "payload": {
        "transaction_id": "uuid",
        "total_amount": 125000,
        "payment_method": "QR_VNPAY",
        ...
      }
    }
  ]
}

Response: 200 OK
{
  "accepted": 1,
  "duplicates": 0
}
```

**Idempotency Implementation**:
```python
async def ingest_event(event: Event):
    # Check inbox for duplicate
    if await inbox_repo.exists(event.event_id):
        return {"status": "duplicate"}
    
    async with transaction():
        # Write to inbox (deduplication)
        await inbox_repo.insert(event.event_id, event.event_type)
        
        # Write to transaction table
        await transaction_repo.insert(event.payload)
        
        # Write to outbox for message broker
        await outbox_repo.insert(event)
    
    return {"status": "accepted"}
```

#### Catalog Service

**Responsibilities**:
- Manage master product catalog
- Version catalog changes
- Generate delta packages for efficient sync

**Database Schema (HQ)**:
```sql
CREATE TABLE catalog_master (
    sku_id VARCHAR(50) PRIMARY KEY,
    barcode VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    base_price DECIMAL(10,2) NOT NULL,
    tax_rate DECIMAL(5,4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    version BIGINT NOT NULL,  -- incremented on update
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_catalog_version ON catalog_master(version);
```

**Sync Protocol**:
- Store requests: `GET /v1/catalog/snapshot?since_version=123`
- HQ responds with delta (items created/updated/deleted since version 123)
- Store applies delta transactionally

#### Pricing Service

Similar to Catalog Service but manages `pricing_master` and `pricing_overrides` (store-specific).

#### Inventory Service

**Responsibilities**:
- Aggregate inventory across stores
- Receive inventory adjustment events
- Trigger replenishment workflows

**Event Consumer**:
```python
async def handle_inventory_adjusted(event):
    await inventory_repo.adjust_stock(
        store_id=event.store_id,
        sku_id=event.sku_id,
        quantity_delta=event.quantity_delta,
        reason=event.reason
    )
    
    # Check if below reorder point
    if await inventory_repo.is_below_reorder_point(sku_id):
        await trigger_replenishment_workflow(sku_id)
```

---

### 5.2 Data Ingestion Pipeline

**Architecture**:
```
Store Edge → gRPC Stream → Ingestion Service → Kafka → Consumers
                                ↓
                          Inbox (Dedup)
                                ↓
                          Transaction DB
```

**Ingestion Service**:
- Implemented in Go or Rust for high throughput
- Stateless, horizontally scalable
- Writes to Kafka topic with partition key = store_id (preserves ordering per store)

**Kafka Topics**:
- `transactions`: All transaction events (SaleRecorded, PaymentCaptured, TransactionVoided)
- `inventory`: Inventory adjustment events
- `catalog-updates`: Master data changes (broadcast to all stores)

**Consumers**:
- Transaction Consumer → Analytics DB (Clickhouse)
- Inventory Consumer → Inventory Service
- Notification Consumer → Alert system

---

## 6. Synchronization Design

### 6.1 Outbox Pattern Implementation

#### Store Edge: Writing to Outbox

```python
async def finalize_transaction(txn_id: UUID, payment_result):
    async with db.transaction():
        # 1. Update transaction status
        await txn_repo.update_status(txn_id, "PAID")
        
        # 2. Update inventory
        await inventory_repo.decrement_stock(txn_id)
        
        # 3. Insert event into outbox (same transaction)
        event = {
            "event_id": uuid4(),
            "event_type": "SaleRecorded",
            "aggregate_type": "Transaction",
            "aggregate_id": str(txn_id),
            "payload": {
                "transaction_id": str(txn_id),
                "store_id": STORE_ID,
                "total_amount": payment_result.amount,
                "line_items": [...],
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await outbox_repo.insert(event)
    
    # Transaction committed atomically
    # Outbox relay will publish this event
```

#### Outbox Relay: Publishing Events

```python
async def relay_loop():
    while True:
        # Poll outbox for unpublished events
        events = await db.execute("""
            SELECT * FROM outbox
            WHERE published_at IS NULL
            ORDER BY id
            LIMIT 50
            FOR UPDATE SKIP LOCKED
        """)
        
        for event in events:
            try:
                # Publish to HQ
                response = await hq_client.publish_event(event)
                
                if response.status == "accepted":
                    # Mark as published
                    await db.execute("""
                        UPDATE outbox
                        SET published_at = NOW(), publish_attempts = publish_attempts + 1
                        WHERE id = $1
                    """, event.id)
                else:
                    # Retry with backoff
                    await db.execute("""
                        UPDATE outbox
                        SET publish_attempts = publish_attempts + 1,
                            last_error = $1
                        WHERE id = $2
                    """, response.error, event.id)
            
            except Exception as e:
                logger.error(f"Failed to publish event {event.id}: {e}")
                await asyncio.sleep(exponential_backoff(event.publish_attempts))
        
        await asyncio.sleep(1)  # Poll interval
```

**Key Properties**:
- `FOR UPDATE SKIP LOCKED`: Allows multiple relay instances without conflict
- Exponential backoff: 1s, 2s, 4s, 8s, ... max 300s
- Infinite retry (events never dropped)

---

### 6.2 Event Types & Schema

#### SaleRecorded
```json
{
  "event_id": "uuid",
  "event_type": "SaleRecorded",
  "store_id": "STORE_001",
  "terminal_id": "POS_03",
  "timestamp": "2026-02-16T11:30:45Z",
  "payload": {
    "transaction_id": "uuid",
    "cashier_id": "CASHIER_007",
    "line_items": [
      {
        "sku_id": "SKU_12345",
        "quantity": 2,
        "unit_price": 25000,
        "line_total": 50000
      }
    ],
    "subtotal": 50000,
    "tax_amount": 5000,
    "discount_amount": 0,
    "total_amount": 55000,
    "payment_method": "QR_VNPAY",
    "payment_provider_ref": "VNPAY_TXN_99887"
  }
}
```

#### InventoryAdjusted
```json
{
  "event_id": "uuid",
  "event_type": "InventoryAdjusted",
  "store_id": "STORE_001",
  "timestamp": "2026-02-16T11:35:00Z",
  "payload": {
    "sku_id": "SKU_12345",
    "adjustment_type": "SALE",  // SALE, SHRINKAGE, RECEIVING, MANUAL
    "quantity_delta": -2,
    "reason": "Transaction completed",
    "reference_id": "transaction_uuid"
  }
}
```

#### PaymentCaptured
```json
{
  "event_id": "uuid",
  "event_type": "PaymentCaptured",
  "store_id": "STORE_001",
  "timestamp": "2026-02-16T11:30:50Z",
  "payload": {
    "transaction_id": "uuid",
    "payment_method": "QR_VNPAY",
    "amount": 55000,
    "provider": "VNPAY",
    "provider_txn_id": "VNPAY_TXN_99887",
    "captured_at": "2026-02-16T11:30:49Z"
  }
}
```

---

### 6.3 Conflict Resolution Strategy

#### Conflict Scenarios

**Scenario 1: Concurrent Price Update**
- Store offline, using price = 10,000 VND
- HQ updates price to 12,000 VND
- Store reconnects and syncs

**Resolution**: Accept store's transaction with old price (transaction is immutable), but apply new price for future transactions. Log price discrepancy for audit.

**Scenario 2: Inventory Discrepancy**
- Store reports stock = 50 after sale
- HQ thinks stock = 52 (didn't receive sale event yet)
- Store sends InventoryAdjusted event

**Resolution**: HQ applies event idempotently (event_id deduplication). Final state converges after all events processed.

**Scenario 3: Duplicate Event (Network Retry)**
- Store sends SaleRecorded event
- HQ processes but ACK lost
- Store retries (sends same event_id again)

**Resolution**: HQ inbox table detects duplicate event_id, returns "accepted" without reprocessing.

#### General Principles
- **Transactions are immutable**: Once PAID, never modified (only voids/refunds)
- **HQ wins for master data**: Latest catalog/pricing version is source of truth
- **Store wins for transactions**: Store's view of transaction is authoritative
- **Eventual consistency**: Tolerate temporary inconsistencies; converge via event replay

---

### 6.4 Network Partition Handling

#### Partition Scenarios

**Full WAN Outage**:
- Store enters offline mode
- All operations continue locally
- Outbox accumulates events
- Upon reconnection, catch-up sync triggered

**Intermittent Connectivity** (Flapping):
- Sync Agent detects flapping (online/offline rapidly)
- Increase health check interval to avoid thrashing
- Use connection pooling with keepalive

**Partial Partition** (Some stores offline):
- HQ continues serving online stores
- Offline stores operate independently
- No cascading failures (stores isolated)

#### Split-Brain Prevention

- Each store has unique store_id (no ambiguity)
- Store cannot impersonate another store (JWT includes store_id claim)
- HQ assigns monotonic transaction IDs per store (not globally)
- No distributed consensus required (stores don't talk to each other)

---

## 7. API Design

### 7.1 Store Edge APIs

#### Checkout API

**Create Transaction**
```
POST /api/v1/transactions
Content-Type: application/json
Authorization: Bearer <cashier_jwt>

{
  "terminal_id": "POS_03",
  "cashier_id": "CASHIER_007"
}

Response: 201 Created
{
  "transaction_id": "uuid",
  "status": "DRAFT",
  "created_at": "2026-02-16T11:30:00Z"
}
```

**Add Item**
```
POST /api/v1/transactions/{txn_id}/items
Content-Type: application/json

{
  "barcode": "8934680083898",
  "quantity": 1
}

Response: 200 OK
{
  "line_item_id": "uuid",
  "sku_id": "SKU_12345",
  "product_name": "Coca Cola 330ml",
  "unit_price": 10000,
  "quantity": 1,
  "line_total": 10000
}
```

**Calculate Total**
```
POST /api/v1/transactions/{txn_id}/calculate
Response: 200 OK
{
  "subtotal": 50000,
  "tax_amount": 5000,
  "discount_amount": 0,
  "total_amount": 55000,
  "applied_promotions": []
}
```

**Initiate Payment**
```
POST /api/v1/transactions/{txn_id}/payments
Content-Type: application/json

{
  "payment_method": "QR_VNPAY",
  "amount": 55000
}

Response: 200 OK
{
  "payment_id": "uuid",
  "qr_code_data": "base64_encoded_qr",
  "expires_at": "2026-02-16T11:31:00Z",
  "status": "PENDING"
}
```

**Poll Payment Status**
```
GET /api/v1/payments/{payment_id}/status

Response: 200 OK
{
  "status": "CAPTURED",  // or PENDING, FAILED
  "provider_txn_id": "VNPAY_TXN_99887",
  "captured_at": "2026-02-16T11:30:45Z"
}
```

**Finalize Transaction**
```
POST /api/v1/transactions/{txn_id}/finalize

Response: 200 OK
{
  "transaction_id": "uuid",
  "status": "PAID",
  "receipt_url": "/api/v1/receipts/{txn_id}"
}
```

#### Catalog API

**Lookup Item by Barcode**
```
GET /api/v1/catalog/items?barcode=8934680083898

Response: 200 OK
{
  "sku_id": "SKU_12345",
  "barcode": "8934680083898",
  "product_name": "Coca Cola 330ml",
  "category": "Beverages",
  "base_price": 10000,
  "tax_rate": 0.10,
  "in_stock": true,
  "available_quantity": 120
}
```

---

### 7.2 HQ Platform APIs

#### Event Ingestion API

```
POST /v1/ingestion/events
Content-Type: application/json
Authorization: Bearer <store_jwt>

{
  "events": [
    {
      "event_id": "uuid",
      "event_type": "SaleRecorded",
      "store_id": "STORE_001",
      "timestamp": "2026-02-16T11:30:45Z",
      "payload": { ... }
    }
  ]
}

Response: 200 OK
{
  "accepted": 1,
  "duplicates": 0,
  "errors": []
}
```

#### Master Data Distribution API

**Get Catalog Snapshot**
```
GET /v1/catalog/snapshot?since_version=123
Authorization: Bearer <store_jwt>

Response: 200 OK
{
  "current_version": 125,
  "items": [
    {
      "sku_id": "SKU_12345",
      "barcode": "8934680083898",
      "product_name": "Coca Cola 330ml",
      "base_price": 10000,
      "tax_rate": 0.10,
      "change_type": "UPDATED"  // CREATED, UPDATED, DELETED
    }
  ]
}
```

---

### 7.3 Sync Protocol

#### gRPC Streaming (Preferred for Real-Time Sync)

**Proto Definition**:
```protobuf
service SyncService {
  rpc StreamEvents(stream EventBatch) returns (stream Acknowledgment);
  rpc PullMasterData(MasterDataRequest) returns (MasterDataResponse);
}

message EventBatch {
  string store_id = 1;
  repeated Event events = 2;
}

message Event {
  string event_id = 1;
  string event_type = 2;
  google.protobuf.Timestamp timestamp = 3;
  google.protobuf.Struct payload = 4;
}

message Acknowledgment {
  repeated string accepted_event_ids = 1;
  repeated string duplicate_event_ids = 2;
  repeated Error errors = 3;
}
```

**Benefits**:
- Bidirectional streaming (store pushes events, HQ pushes acks)
- Low latency (persistent connection)
- Automatic reconnection with backoff
- Multiplexing (multiple streams over one connection)

---

## 8. Technology Stack

### Store Edge

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **API Framework** | FastAPI (Python) | Async support, fast development, great for CRUD APIs |
| **Database** | PostgreSQL 15 | ACID compliance, JSON support, mature replication |
| **Outbox Relay** | Python (asyncio) | Simple, can embed in FastAPI or run standalone |
| **Sync Agent** | Python (asyncio) | Stateful sync logic, easy to debug |
| **Container Runtime** | Docker / k3s | Lightweight, easy deployment |
| **Reverse Proxy** | NGINX | Load balancing, SSL termination |

**Alternative Considerations**:
- **Edge DB**: SQLite (lighter, but lacks replication features)
- **Edge API**: Rust/Actix (faster, but steeper learning curve)

### HQ Platform

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Ingestion Service** | Go / Rust | High throughput, low latency |
| **Transaction Service** | FastAPI or Go | Stateless, horizontally scalable |
| **Catalog/Pricing Service** | FastAPI | CRUD-heavy, benefits from async Python |
| **Message Broker** | Redpanda or Kafka | Event streaming, ordering guarantees |
| **Transaction DB** | PostgreSQL (primary) | ACID, complex queries |
| **Analytics DB** | Clickhouse | Column-oriented, fast aggregations |
| **Identity Service** | Keycloak or custom (FastAPI + JWT) | OAuth2/OIDC support |
| **Reporting** | Metabase or custom (FastAPI + React) | SQL-based dashboards |
| **Container Orchestration** | Kubernetes (EKS/GKE) | Production-grade, auto-scaling |
| **API Gateway** | Kong or NGINX | Rate limiting, authentication |

**Alternative Considerations**:
- **Message Broker**: NATS JetStream (simpler ops than Kafka)
- **Analytics DB**: TimescaleDB (if time-series focus)

### DevOps & Observability

| Tool | Purpose |
|------|---------|
| **Monitoring** | Prometheus + Grafana |
| **Logging** | Loki or ELK Stack |
| **Tracing** | Jaeger or Tempo |
| **CI/CD** | GitHub Actions or GitLab CI |
| **IaC** | Terraform |
| **Config Management** | Ansible (for edge servers) |

---

## 9. Deployment Architecture

### Store Edge Deployment

**Physical Setup**:
- Mini PC (Intel NUC or Raspberry Pi 4+ for budget)
- 8GB RAM, 256GB SSD
- Dual network: Ethernet (primary), 4G/5G USB modem (backup)

**Software Deployment**:
```bash
# On each store edge server
docker-compose up -d

# docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: <encrypted>
  
  edge-api:
    image: circle-k-edge-api:v1.0.0
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://...
      STORE_ID: STORE_001
      HQ_ENDPOINT: https://hq.circlek.vn
  
  outbox-relay:
    image: circle-k-outbox-relay:v1.0.0
    depends_on:
      - postgres
  
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

**Update Strategy**:
- Blue-green deployment (run new version alongside old)
- Health check before switching traffic
- Automatic rollback if health check fails
- Scheduled updates during low-traffic hours (3-5 AM)

### HQ Platform Deployment

**Cloud Architecture** (AWS Example):
```
┌─────────────────────────────────────────┐
│          Route 53 (DNS)                 │
└─────────────────────────────────────────┘
                  │
┌─────────────────────────────────────────┐
│     CloudFront / ALB (Load Balancer)    │
└─────────────────────────────────────────┘
                  │
┌─────────────────────────────────────────┐
│      EKS (Kubernetes Cluster)           │
│  ┌─────────────┐  ┌─────────────┐      │
│  │ Ingestion   │  │ Transaction │      │
│  │ Service     │  │ Service     │      │
│  │ (Go)        │  │ (FastAPI)   │      │
│  └─────────────┘  └─────────────┘      │
│                                          │
│  ┌─────────────┐  ┌─────────────┐      │
│  │ Catalog     │  │ Inventory   │      │
│  │ Service     │  │ Service     │      │
│  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────┘
                  │
┌─────────────────────────────────────────┐
│       MSK (Managed Kafka)               │
└─────────────────────────────────────────┘
                  │
┌─────────────────────────────────────────┐
│  RDS (Postgres) + Read Replicas         │
│  Clickhouse (Analytics)                 │
└─────────────────────────────────────────┘
```

**Scaling Strategy**:
- **Ingestion Service**: Auto-scale based on Kafka consumer lag
- **Transaction Service**: Auto-scale based on CPU (target: 60%)
- **Database**: Read replicas for reporting queries
- **Kafka**: 3-broker cluster (min), partition by store_id

---

## 10. Security Design

### Authentication & Authorization

**Store Edge**:
- Cashiers authenticate with PIN (local verification against synced user table)
- Edge server holds JWT issued by HQ Identity Service
- JWT includes claims: `store_id`, `terminal_id`, `roles`
- JWT refresh token stored securely (encrypted at rest)

**HQ Platform**:
- All API calls require valid JWT in `Authorization: Bearer` header
- JWT validated using public key (RS256)
- Role-based access control (RBAC):
  - `cashier`: Create transactions, finalize payments
  - `manager`: Void transactions, adjust inventory, view reports
  - `admin`: Manage users, configure pricing, access audit logs

### Data Protection

**In Transit**:
- TLS 1.3 for all HTTPS connections
- Mutual TLS (mTLS) for store-to-HQ communication (optional)
- gRPC with TLS for streaming

**At Rest**:
- Database encryption using LUKS (store edge) or cloud-native encryption (HQ)
- Sensitive fields (payment provider secrets) encrypted with application-level key (AES-256)
- Secrets managed via HashiCorp Vault or AWS Secrets Manager

**PCI DSS Compliance** (for QR payments):
- No cardholder data stored (QR redirects to provider)
- Payment provider references stored (non-sensitive)
- Audit logs retained for 7 years

### Network Security

**Store Edge**:
- Firewall: Allow only outbound HTTPS to HQ endpoints
- VPN optional (adds complexity, but increases security)

**HQ Platform**:
- VPC with private subnets for databases
- Security groups: Allow only necessary ports
- Web Application Firewall (WAF) on ALB to block common attacks

---

## 11. Monitoring & Observability

### Metrics (Prometheus)

**Store Edge Metrics**:
```
# Business Metrics
transactions_created_total{store_id, terminal_id}
transactions_completed_total{store_id, terminal_id, payment_method}
transaction_amount_sum{store_id}

# System Metrics
api_request_duration_seconds{endpoint, method}
database_query_duration_seconds{query_type}
outbox_queue_length{store_id}
outbox_publish_attempts_total{store_id, success}
```

**HQ Platform Metrics**:
```
# Ingestion
events_received_total{store_id, event_type}
events_duplicate_total{store_id}
events_processing_duration_seconds

# Kafka
kafka_consumer_lag{topic, consumer_group}

# Services
service_request_duration_seconds{service, endpoint}
service_error_rate{service}
```

### Logging (Structured JSON)

**Log Format**:
```json
{
  "timestamp": "2026-02-16T11:30:45Z",
  "level": "INFO",
  "service": "checkout-api",
  "store_id": "STORE_001",
  "terminal_id": "POS_03",
  "trace_id": "abc123",
  "message": "Transaction finalized",
  "context": {
    "transaction_id": "uuid",
    "total_amount": 55000,
    "payment_method": "QR_VNPAY"
  }
}
```

### Tracing (Distributed)

- Propagate `trace_id` across all service calls
- Use OpenTelemetry SDK
- Visualize traces in Jaeger or Grafana Tempo

**Example Trace**:
```
[STORE_001/POS_03] POST /api/v1/transactions/{id}/finalize
  ├─ [DB] UPDATE transactions SET status = 'PAID'
  ├─ [DB] UPDATE inventory SET current_stock = current_stock - 2
  ├─ [DB] INSERT INTO outbox (...)
  └─ [HQ] gRPC StreamEvents (event_id=xyz)
      ├─ [HQ Ingestion] Check inbox for duplicate
      ├─ [HQ DB] INSERT INTO transactions (...)
      └─ [Kafka] Publish to topic=transactions
```

### Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Store Offline | `system_status.is_online = false` for > 10 min | Warning | Notify store manager |
| Outbox Backlog | `outbox_queue_length > 1000` | Warning | Investigate network |
| Payment Failure Rate High | `payment_failures / payment_attempts > 0.1` | Critical | Check payment provider |
| Database Disk Full | Disk usage > 90% | Critical | Immediate intervention |
| HQ Ingestion Lag | Kafka consumer lag > 1000 | Warning | Scale ingestion service |

---

## 12. Testing Strategy

### Unit Tests

**Store Edge**:
- Test API endpoints with mocked database
- Test outbox relay logic with mocked HQ client
- Test payment state machine transitions

**HQ Platform**:
- Test event ingestion with duplicate events
- Test idempotency logic (inbox pattern)
- Test catalog delta generation

### Integration Tests

**Store Edge**:
- Test full checkout flow (create → add items → pay → finalize)
- Test offline mode (disconnect network, verify transactions continue)
- Test sync catch-up (reconnect, verify events published)

**HQ Platform**:
- Test end-to-end event ingestion (store → ingestion → Kafka → consumer)
- Test master data distribution (HQ updates → store pulls → local DB updated)

### Load Tests

**Store Edge**:
- Simulate 5 concurrent POS terminals
- Each terminal: 20 transactions/hour
- Verify response times < 300ms (p95)

**HQ Platform**:
- Simulate 100 stores sending events simultaneously
- 10,000 events/minute
- Verify ingestion lag < 5 seconds

### Chaos Tests

**Network Partition**:
- Disconnect store from HQ randomly
- Verify store continues operating
- Verify sync resumes upon reconnection

**Database Failure**:
- Kill Postgres on store edge
- Verify automatic restart and WAL recovery

**Message Broker Failure**:
- Stop Kafka cluster
- Verify ingestion service retries
- Verify no data loss after Kafka recovery

---

## 13. Implementation Roadmap

### Phase 1: MVP (4-6 weeks)

**Goal**: Single store with 1 POS terminal, basic checkout, offline mode

**Deliverables**:
- Store Edge API (checkout, catalog)
- Local Postgres with core tables
- Outbox pattern implementation
- Basic HQ ingestion service (HTTP endpoint)
- Manual testing

### Phase 2: Multi-Terminal + Sync (4-6 weeks)

**Goal**: 5 POS terminals, real-time sync to HQ

**Deliverables**:
- Outbox relay with retry logic
- gRPC streaming (store → HQ)
- HQ ingestion service with Kafka
- Master data distribution (catalog/pricing)
- Integration tests

### Phase 3: Payment Integration (2-3 weeks)

**Goal**: QR payment with VNPay/MoMo

**Deliverables**:
- Payment gateway integration
- QR code generation
- Payment polling mechanism
- Payment reconciliation reports

### Phase 4: Multi-Store Rollout (3-4 weeks)

**Goal**: 10 stores in production

**Deliverables**:
- Store provisioning automation (Ansible playbooks)
- Centralized monitoring dashboards
- Alerting rules
- Runbooks for common issues

### Phase 5: Advanced Features (Ongoing)

- Loyalty program integration
- Promotion engine
- Advanced reporting (BI dashboards)
- Predictive inventory replenishment
- Self-checkout kiosk support

---

## 14. Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| **Outbox Pattern** | Design pattern where events are written to a local outbox table in the same transaction as business data, then published asynchronously by a relay process |
| **Inbox Pattern** | Design pattern for idempotent event consumption; incoming events are checked against an inbox table to detect duplicates |
| **Event Sourcing** | Architectural pattern where state changes are stored as a sequence of immutable events |
| **Transactional Outbox** | Combination of outbox pattern with ACID transactions to ensure reliable message delivery |
| **Sync Cursor** | Pointer tracking the last synchronized version of master data (e.g., catalog_version = 125) |
| **Edge Computing** | Paradigm where computation is performed close to data sources (stores) rather than centralized cloud |

### B. References

- [Transactional Outbox Pattern - Microservices.io](https://microservices.io/patterns/data/transactional-outbox.html)
- [Event Sourcing Pattern - Microsoft Azure](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)
- [Offline POS Functionality - Dynamics 365](https://learn.microsoft.com/en-us/dynamics365/commerce/dev-itpro/pos-offline-functionality)
- [Retail Edge Architecture - VMware](https://www.vmware.com/docs/vmware-retail-edge-architecture)

### C. Sample Calculations

**Store Edge Hardware Sizing**:
- Transactions per day: 500
- Average transaction size: 5 items
- Database writes per transaction: ~15 rows (transaction + line_items + payments + outbox)
- Total writes per day: 7,500 rows
- Storage growth: ~50MB/month (conservative)
- **Recommended**: 256GB SSD (5+ years before disk replacement)

**HQ Ingestion Capacity**:
- 100 stores × 500 transactions/day = 50,000 transactions/day
- Peak load: 10× average = 500,000 transactions/day = ~6 transactions/second
- With event batching (50 events/batch): 0.12 batches/second
- **Ingestion Service**: 2-4 instances handle peak comfortably

**Kafka Partition Sizing**:
- Partition key: `store_id`
- 100 stores → 100 partitions ideal (1 partition per store for ordering)
- 3 brokers × 100 partitions = 300 total partition-replicas
- **Throughput**: Each partition handles 10MB/s+ (far exceeds our ~1KB/s per store)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-16 | System Design Practice | Initial draft with SRD + detailed design |

---

**End of Document**

This system design document provides a comprehensive blueprint for building a Circle K-style convenience store POS system with offline-first architecture and real-time HQ synchronization. Use this as a learning resource for system design practice, adapting components and technologies based on your specific requirements and constraints.

For implementation questions or clarifications, refer to the referenced resources or conduct deeper research into specific patterns (Outbox, Event Sourcing, gRPC streaming).