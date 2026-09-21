# 🛡️ DBPTBS

## DNA Behavioural Pre-Transaction Blockchain Security System

> **"Don't just verify where the money is going. Verify who is actually sending it."**

DBPTBS is a **behavioural authentication and risk-assessment security layer for blockchain transactions**. It analyzes a user's behavioural and transactional patterns, creates a unique **Digital DNA**, and evaluates whether a new transaction is consistent with the legitimate account owner's established behaviour.

The system is designed to detect potentially unauthorized transactions **before they are executed on the blockchain**.

---
## 🚀 How to Run

<details>
<summary><b>Click here to see installation & run instructions</b></summary>

### 🪟Windows

```bash```

<b>1. Clone the repo</b> 

```git clone https://github.com/ghulehasya/DBPTBS-System.git```


<b>2. Run the commands as following</b>

 ```python -m venv .venv```
 
```.venv\Scripts\activate```

``` pip install -r requirements.txt```

```streamlit run dashboard.py```

---

### 🍎macOS / 🐧Linux

<b>1. Clone the repo</b> 

```git clone https://github.com/ghulehasya/DBPTBS-System.git```

<b>2. Run the commands as following</b>

 ```python3 -m venv .venv```

```source .venv/bin/activate ```

``` pip install -r requirements.txt ```

```streamlit run dashboard.py ```

</details>

---

## 🔴 Problem Statement

Blockchain provides strong transaction integrity, but transaction integrity alone does not prove that the person initiating a transaction is the legitimate account owner.

Consider a compromised cryptocurrency wallet:

* An attacker obtains valid credentials or session access.
* The recipient wallet may be completely legitimate.
* The transaction can therefore appear valid to conventional security systems.
* However, the person initiating the transaction may not be the actual account owner.

Traditional fraud detection often focuses on:

> **"Where is the money going?"**

DBPTBS adds another security question:

> **"Who is actually sending the money?"**

---

## 🟢 Proposed Solution

DBPTBS introduces a **pre-transaction behavioural security layer** between the user and the blockchain.

The system learns the legitimate user's normal behavioural patterns and builds a **Digital DNA / Behavioural Profile**.

Before allowing a transaction to proceed, DBPTBS compares the current transaction and interaction behaviour against this established baseline.

### Core Flow

```text
User Activity
      ↓
Behavioural Feature Extraction
      ↓
Digital DNA / Behavioural Profile
      ↓
Behavioural Comparison
      ↓
Risk Score
      ↓
 ┌───────────────┬────────────────────┐
 │   Low Risk    │     High Risk      │
 ↓               ↓                    │
Proceed      Block / Verify           │
 ↓               ↓                    │
Blockchain   Additional Auth          │
```

---

# 🧬 Digital DNA

The **Digital DNA** represents the behavioural characteristics normally associated with a legitimate user.

Depending on the implementation and available data, DBPTBS can analyze signals such as:

| Behavioural Signal        | Example                                 |
| ------------------------- | --------------------------------------- |
| 💰 Transaction Amount     | Typical transaction value/range         |
| 🕐 Transaction Time       | Normal transaction hours                |
| 🔄 Transaction Frequency  | Typical transaction frequency           |
| 👤 Recipient Behaviour    | Frequently used/trusted recipients      |
| 🖱️ Interaction Behaviour | Mouse movement and interaction patterns |
| ⌨️ Input Behaviour        | Typing and navigation patterns          |
| 📱 Application Behaviour  | Application usage patterns              |
| 💻 Device Context         | Device/session characteristics          |
| 🌐 Session Context        | Contextual session characteristics      |

These signals are combined rather than relying on a single indicator.

---

# 🧠 Behavioural Baseline

DBPTBS first establishes a baseline of normal user behaviour.

For example, a user may normally perform:

```text
Transaction Amount : ₹500 – ₹2,000
Recipients         : Known contacts
Transaction Time   : Evening
Frequency           : Low / Moderate
Interaction         : Consistent
```

A new transaction may instead look like:

```text
Transaction Amount : ₹50,000
Recipient           : Unknown wallet
Transaction Time    : Unusual hour
Interaction          : Abnormal
```

The system does **not** automatically consider a transaction suspicious simply because the amount is large.

Instead, it evaluates the **combined deviation across multiple behavioural signals**.

---

# 📊 Risk Assessment

The extracted behavioural features are compared against the user's Digital DNA.

A conceptual risk model can be represented as:

```text
Behavioural Deviation
        +
Transaction Deviation
        +
Contextual Deviation
        ↓
   Risk Calculation
        ↓
   Risk Classification
```

### Example Decision Model

```text
             Transaction Request
                     ↓
             Feature Extraction
                     ↓
          Compare with Digital DNA
                     ↓
                Risk Score
              /            \
         Low Risk         High Risk
            ↓                ↓
      Allow Transaction   Block Temporarily
                              ↓
                    Additional Authentication
                         /           \
                    Verified       Failed
                       ↓              ↓
                   Proceed         Block
```

---

# 🚨 Compromised Account Scenario

Imagine an attacker gains access to a user's cryptocurrency wallet.

The attacker may have:

* Valid credentials
* A valid session
* Access to the wallet
* A legitimate recipient address

However, their behavioural pattern may differ significantly from the legitimate user.

DBPTBS can detect deviations across multiple signals and assign an elevated risk score.

### Security Workflow

```text
Payment Request
      ↓
Behavioural Analysis
      ↓
Suspicious Activity Detected
      ↓
Transaction Temporarily Blocked
      ↓
Session Restricted
      ↓
Additional Authentication
      ↓
 ┌─────────────────────┐
 │                     │
Verified Owner     Verification Failed
 │                     │
 ↓                     ↓
Transaction          Transaction
Allowed              Blocked

```

---

# ⚡ What Makes DBPTBS Different?

Conventional transaction security can focus heavily on transaction validity and recipient legitimacy.

DBPTBS introduces **behavioural authentication before transaction execution**.

### Traditional Approach

```text
Credentials
     ↓
Account
     ↓
Transaction
     ↓
Blockchain
```

### DBPTBS Approach

```text
User Behaviour
     ↓
Behavioural DNA
     ↓
Risk Assessment
     ↓
Authentication
     ↓
Transaction
     ↓
Blockchain
```

DBPTBS is intended to work as an **additional security layer**, complementing existing authentication and blockchain mechanisms.

---

# 🔥 Core Innovation

The central innovation of DBPTBS is the combination of:

* 🧬 Behavioural profiling
* 📊 Anomaly detection
* 🎯 Risk scoring
* 🔐 Pre-transaction authentication
* ⛓️ Blockchain transaction security

Instead of evaluating only the transaction itself, the system evaluates the **behaviour surrounding the transaction**.

---

# 🎯 Objectives

DBPTBS aims to:

* Detect potentially unauthorized blockchain transactions.
* Identify behavioural deviations from a legitimate user's baseline.
* Generate a transaction risk score before execution.
* Temporarily block suspicious transactions.
* Trigger additional authentication when required.
* Provide an additional security layer for compromised accounts.
* Reduce the risk associated with unauthorized transactions.

---

# 🏗️ System Architecture

A high-level architecture can be represented as:

```text
                    ┌──────────────────┐
                    │      User        │
                    └────────┬─────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │ Behaviour Collection│
                  └──────────┬──────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │ Feature Extraction  │
                  └──────────┬──────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │   Digital DNA       │
                  │ Behavioural Profile │
                  └──────────┬──────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │ Behaviour Comparison│
                  └──────────┬──────────┘
                             │
                             ↓
                  ┌─────────────────────┐
                  │    Risk Scoring     │
                  └──────────┬──────────┘
                             │
                    ┌────────┴────────┐
                    ↓                 ↓
               Low Risk          High Risk
                    ↓                 ↓
             Allow Transaction   Block / Verify
                    ↓                 ↓
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │    Blockchain   │
                    └─────────────────┘
```

---

# 🔐 Security Layers

DBPTBS can operate alongside existing security mechanisms rather than replacing them.

```text
┌─────────────────────────────────────┐
│ Existing Authentication             │
├─────────────────────────────────────┤
│ Wallet / Account Security            │
├─────────────────────────────────────┤
│ DBPTBS Behavioural Security Layer    │
├─────────────────────────────────────┤
│ Risk Assessment                      │
├─────────────────────────────────────┤
│ Additional Authentication            │
├─────────────────────────────────────┤
│ Blockchain Transaction               │
└─────────────────────────────────────┘
```

---

# 💡 Example

### Normal Behaviour

```text
User:
    ₹500 – ₹2,000 transactions
    Known recipients
    Evening activity
    Consistent interaction patterns
```

### Current Transaction

```text
Transaction:
    ₹50,000
    Unknown recipient
    Unusual transaction time
    Abnormal interaction pattern
```

### DBPTBS

```text
Current Behaviour
       ↓
Compare with Digital DNA
       ↓
Significant Behavioural Deviation
       ↓
Elevated Risk Score
       ↓
Additional Verification
```

This allows suspicious activity to be investigated **before the transaction is finalized**.

---

# 🛠️ Technology Domain

DBPTBS combines concepts from multiple technology areas:

* **Blockchain**
* **Cybersecurity**
* **Behavioural Analytics**
* **Anomaly Detection**
* **Fraud Detection**
* **Risk Assessment**
* **Authentication**
* **Machine Learning / Data Analysis**
* **Transaction Security**

---

# 📁 Project Structure

The exact structure may vary depending on the implementation. A typical structure can be organized as:

```text
DBPTBS/
│
├── backend/
│   ├── models/
│   ├── services/
│   ├── routes/
│   └── database/
│
├── frontend/
│   ├── components/
│   ├── pages/
│   └── assets/
│
├── blockchain/
│   ├── contracts/
│   └── transactions/
│
├── behavioural_analysis/
│   ├── feature_extraction/
│   ├── profiling/
│   └── risk_scoring/
│
├── docs/
│
├── tests/
│
├── requirements.txt
├── package.json
└── README.md
```

---

# 🚀 Future Scope

DBPTBS can be extended with additional capabilities such as:

* 🤖 Machine-learning-based behavioural modelling
* 📈 Adaptive user baselines
* 🧠 Continuous behavioural learning
* 🔍 Advanced anomaly detection
* 🔐 Multi-factor authentication integration
* ⛓️ Smart-contract integration
* 📱 Mobile behavioural signals
* 💻 Advanced device fingerprinting
* 🚨 Real-time security alerts
* 📊 Security dashboards and analytics
* 🔄 Continuous risk assessment during active sessions

---

# ⚠️ Important Considerations

Behavioural authentication should be treated as an **additional security signal**, not an infallible identity proof.

User behaviour can naturally change due to new devices, locations, accessibility requirements, travel, or unusual but legitimate transactions. A production implementation should therefore account for behavioural variation and provide appropriate recovery and authentication mechanisms.

The prototype is intended to demonstrate the concept of **pre-transaction behavioural security for blockchain systems**.

---

# 🎯 Core Idea

> ### **Don't just verify where the money is going. Verify who is actually sending it.**

DBPTBS aims to move blockchain transaction protection from **transaction-only verification** toward **human-behaviour-aware security**.

```text
          WHO IS SENDING?
                 +
          WHERE IS IT GOING?
                 ↓
        PRE-TRANSACTION RISK
                 ↓
          SECURE EXECUTION
```

--- 
## 📸 Screen Shots
<img width="1917" height="972" alt="Screenshot 2026-09-18 015131" src="https://github.com/user-attachments/assets/fe04ce52-228f-4df6-92c6-48f619559d2c" />
<img width="1917" height="971" alt="Screenshot 2026-09-18 015326" src="https://github.com/user-attachments/assets/ea3e3f7d-6aa5-43ca-9f53-c80409e95920" />
<img width="1916" height="971" alt="Screenshot 2026-09-18 015349" src="https://github.com/user-attachments/assets/1b876625-7b0d-48ed-9b27-01440e71316c" />
<img width="1917" height="970" alt="Screenshot 2026-09-18 015421" src="https://github.com/user-attachments/assets/64cf694f-3b01-4569-9a37-a89ff5d11b67" />
<img width="1917" height="971" alt="Screenshot 2026-09-18 015442" src="https://github.com/user-attachments/assets/e6e6f4d2-ecfc-4927-8f2a-760ba6422183" />
<img width="1917" height="972" alt="Screenshot 2026-09-18 015458" src="https://github.com/user-attachments/assets/c9a97df1-7a2e-43ff-974c-586a3a712526" />


---
## 📌 Project Status

**🚧 Hackathon Prototype / Research Project**

DBPTBS is a conceptual and prototype security framework demonstrating how behavioural analytics can be incorporated into blockchain transaction workflows.

---

## 👥 Contributors

1. Hasya Ghule
2. Avdhut Parvate
