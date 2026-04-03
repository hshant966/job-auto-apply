# Prompt Engineering Guide — JobAutoApply

## Overview

This guide documents all prompt engineering techniques used in the JobAutoApply AI system. Every AI interaction uses carefully crafted prompts with specific techniques for reliability and quality.

---

## Core Techniques

### 1. Chain-of-Thought (CoT)

**Used in:** Job matching, failure analysis, ATS scoring

Force the model to reason step-by-step before producing a score or recommendation. This dramatically improves accuracy.

**Pattern:**
```
Think through this step-by-step:
1. First, analyze X...
2. Then, evaluate Y...
3. Finally, determine Z...
```

**Why it works:** Reduces hallucination by forcing the model to show its work. Each step constrains the next.

### 2. Few-Shot Learning

**Used in:** All roles

Provide 2-3 examples of input→output pairs. This calibrates the model's output format and quality expectations.

**Pattern:**
```
Example 1:
Input: [specific input]
Output: [specific output]

Example 2:
Input: [different input]
Output: [different output]

Now handle this:
Input: {{actual_input}}
Output:
```

### 3. Structured Output (JSON)

**Used in:** All roles except cover letter

Enforce JSON output with explicit schemas. This ensures parseable, consistent responses.

**Pattern:**
```
Return your response as JSON matching this schema:
{
  "field1": "string",
  "field2": number,
  "field3": ["array", "of", "items"]
}
```

**Anti-hallucination tip:** Include field descriptions and validation rules in the schema.

### 4. Role Prompting

**Used in:** All interactions

Start with a clear persona. This focuses the model's knowledge and behavior.

**Pattern:**
```
You are a [specific expert] with [X years] of experience in [domain].
You specialize in [specific skill].
Your core principle: [key behavior constraint].
```

### 5. Constitutional Constraints

**Used in:** Resume optimizer, screening QA

Set hard rules that the model must never violate. Use NEVER/ALWAYS for clarity.

**Pattern:**
```
You must NEVER:
- [critical constraint 1]
- [critical constraint 2]

You should ALWAYS:
- [positive behavior 1]
- [positive behavior 2]
```

---

## Template Syntax

All prompt templates use `{{variable_name}}` for substitution.

### Variable Naming Convention
- `{{candidate_profile}}` — Full candidate JSON/text
- `{{job_description}}` — Raw job description text
- `{{company_name}}` — Target company
- `{{question}}` — Screening question text
- `{{question_type}}` — Category (salary, experience, etc.)
- `{{original_resume}}` — Current resume text
- `{{target_job_title}}` — Job title being applied for

### Conditional Sections
```
{{#if is_government}}
Additional rules for government portal applications:
- Use formal language
- Include reservation category if applicable
- Reference specific qualification requirements
{{/if}}
```

---

## Quality Assurance

### Validation Prompt
After generating output, run a validation check:
```
Review this AI-generated response for:
1. Factual consistency with input data
2. JSON schema compliance
3. Appropriate confidence levels
4. No hallucinated information

Input: [original input]
Output: [generated output]
Issues found: [list or "None"]
```

### Regression Testing
Maintain a set of test cases:
```json
{
  "test": "job_match_strong_python",
  "input": {"candidate": "...", "job": "..."},
  "expected": {"min_score": 75, "recommendation": "APPLY"},
  "actual": null
}
```

### A/B Testing Framework
Track prompt variant performance:
- Variant A: CoT included → 82% accuracy
- Variant B: No CoT → 64% accuracy
- Winner: Variant A (statistically significant)

---

## Anti-Patterns

### ❌ Don't: Open-ended prompts
```
"Tell me about this resume"
```
→ Unpredictable output, hard to parse.

### ✅ Do: Constrained prompts
```
"Score this resume's ATS compatibility on a 0-100 scale. Return JSON with breakdown."
```

### ❌ Don't: Assume context
```
"Optimize it for the job"
```
→ Model doesn't know which job.

### ✅ Do: Provide full context
```
"Optimize this resume: [resume] for this job: [job_description]"
```

### ❌ Don't: Trust single outputs
→ Always validate critical outputs (scores, recommendations).

### ✅ Do: Self-consistency
→ Run matching 3 times, take majority vote for reliability.

---

## Token Management

| Prompt Type | Avg Tokens In | Avg Tokens Out | Max Budget |
|-------------|---------------|----------------|------------|
| Job Match | 800 | 300 | 1500 |
| Resume Optimize | 1500 | 2000 | 4000 |
| Cover Letter | 1000 | 400 | 1500 |
| Screening QA | 500 | 150 | 800 |
| Failure Analysis | 600 | 400 | 1000 |
| ATS Score | 1200 | 500 | 2000 |

---

## Multi-Language Support

For Hindi job descriptions or mixed-language contexts:
```
The job description may be in Hindi or English. Analyze it in the language it's written. Your response should match the language of the job description.
```
