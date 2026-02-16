# User's manual: Specification-driven development (SDD)

This manual guides you through the Specification-Driven Development (SDD) methodology for building software features. You'll learn how to create comprehensive SPECs that define **what** to build, detailed PLANs that specify **how** to implement it, and best practices for working effectively with AI assistants throughout the development lifecycle.

---

## 🎯 Recommendation: Iterative development with SDD

### Progressive context building

Working with **Specification-Driven Development (SDD)** improves significantly when documented iteratively:

- **Related features**: Upon completing a feature, you can start another related one by referencing the previous
- **Cumulative context**: Each documented SPEC and PLAN enriches the project context
- **Agent learning**: Developing multiple features with this framework allows the agent to:
  - Better understand the project architecture
  - Maintain consistency in implementation patterns
  - Reuse previous solutions and structures
  - Reduce specification time for similar features

### Benefits of the iterative approach

- **Living documentation**: The history of SPECs and PLANs serves as evolving project documentation
- **Continuous improvement**: Each iteration refines the process and specification quality
- **Shared knowledge**: Facilitates onboarding of new developers to the project
- **Traceability**: Maintains a clear record of technical and business decisions

> **Recommendation**: Organize features in folders within `specs/` and maintain cross-references between related features. This creates a knowledge graph that enhances AI-assisted development.

### Encourage clarification questions

Instruct the agent to ask questions when encountering ambiguous or unclear requirements. This prevents assumptions and ensures accurate specifications.

**Example prompt**:
```
"@spec-template create a spec considering: {your spec definition here}. 
If you encounter any ambiguous requirements, unclear business rules, or 
missing information, please ask me clarifying questions before making 
assumptions. I prefer to provide explicit guidance rather than having 
you infer unclear details."
```

---

## What is a SPEC?

A **SPEC** is a specification document that defines **WHAT** should be built, without entering into implementation details.

### Required content

- **Use case**: Description of the problem to solve and user flows
- **Functional requirements**: What the system should do
- **Non-functional requirements**: Performance, security, scalability
- **Acceptance criteria**: Conditions that determine if the solution is successful
- **Business goals**: High-level objectives that justify the development
- **Error handling**: Expected behavior in unexpected situations

### Fundamental principles

✅ **Do:**
- Constantly review the document
- Explain the **WHAT** will be accomplished
- Include high-level technical requirements

### Recommendations

- **Tools**: Use Fury for Development MCP for platform and SDK context or backend namespace MCP 
- **References**: Include project documentation, existing rules, Figma images or screenshots, and relevant technical guides so the agent can understand the context and create a better definition in the spec
- **Suggested models**: "gpt-5.1-codex", "gpt-5-codex", "gpt-5.1" or "gemini-2.5-pro" (models with reasoning and thinking capabilities)
- **Don't include** implementation details, code snippets or file paths.
- **No suggested models**: Cursor's "composer-1" model

---

## What is a PLAN?

A **PLAN** is a technical document that defines **HOW** the solution described in the SPEC will be implemented.

### Required content

- **Technical design**: Architecture and solution components
- **Implementation**: How the SPEC requirements will be covered
- **Libraries and dependencies**: Libraries, SDKs, and frameworks to use
- **Data structures**: Database models, schemas, migrations
- **API contracts**: Request/response bodies, headers, status codes
- **Testing strategy**: Types of tests (unit, integration, e2e) and expected coverage
- **Detailed tasks**: Granular list of activities to complete (can be in a separate file)

### Fundamental principles

✅ **Do:**
- Cover all SPEC requirements
- Explain the **HOW** it will be accomplished
- Detail the project-specific implementation
- Include tasks with high granularity

### Recommendations

- **Format**: `.md` file or IDE/CLI "plan mode" tools
- **References**: Include existing project files as examples of similar implementation
- **Suggested models**: Use "claude-sonnet-4.5" or "gpt-5.1-codex" for coding tasks and implementation; "gpt-5.1-codex-mini" for cost-efficient changes; "gpt-5.1" to make plans

#### ⚠️ Critical plan review

Exhaustive plan review is **fundamental** before starting implementation:

- **Task completeness**: Verify that all implementation and testing tasks are present
- **Development criteria**: Validate compliance with code standards, conventions, and project best practices
- **Architecture**: Review that the proposed design is coherent with the existing architecture
- **Testing coverage**: Confirm that unit, integration, and e2e tests are included as appropriate
- **Dependencies**: Validate that all necessary libraries and SDKs are identified and correct
- **API contracts**: Verify that all endpoints, requests, and responses are defined
- **Error handling**: Ensure that error and recovery scenarios are contemplated
- **Iteration**: Review and refine the plan until it covers all SPEC requirements

> **Important**: An error or lack of detail in the plan will propagate to the implementation. Investing time in review avoids later re-work.

---

## 🚀 When to start implementation?

Implementation should start **only** when the following quality criteria are met:

### Approval criteria to start development

#### ✅ Validated SPEC
- **Complete review**: The SPEC has been thoroughly reviewed
- **Use cases covered**: All use cases and user flows are documented
- **Clear requirements**: Functional and non-functional requirements are specific and measurable
- **Acceptance criteria**: They are defined and verifiable

#### ✅ Complete PLAN
- **Defined architecture**: The technical design is coherent with the existing project
- **Implemented flows**: All data and control flows are specified
- **Error handling**: Error and recovery scenarios are contemplated
- **Incorporated testing**: The testing strategy (unit, integration, e2e) is defined
- **Granular tasks**: All implementation tasks are identified and prioritized
- **Identified dependencies**: Libraries, SDKs, and external services are specified

### ⚠️ If criteria are not met

**DO NOT start implementation**. Instead:

1. Identify missing or incomplete areas
2. Review and complete the SPEC and/or PLAN as appropriate
3. Iterate until all approval criteria are met
4. Validate again before proceeding

### Benefits of this discipline

- **Efficient implementation**: Code flows naturally following the plan
- **Less re-work**: Errors detected in specification are cheaper to fix
- **Higher quality**: Testing is integrated from the design phase
- **Better estimation**: Granular tasks allow precise progress tracking
- **Bug reduction**: Edge cases and error handling are contemplated from the start

> **Golden rule**: If you have doubts about the completeness of the SPEC or PLAN, **DO NOT implement**. Invest time in clarifying first. One hour of planning saves hours or days of corrections.

---

## Workflow

```
1. SPEC → Defines WHAT to build (without implementation)
2. PLAN → Defines HOW to build (with implementation)
3. Development → Executes the plan
```

---

## 📋 Template usage

The SPEC and PLAN templates located in `specs/templates/` provide a standardized structure for documentation.

### ⚠️ Important

- **Do not modify templates**: Files in `specs/templates/` should remain unchanged
- **Copy and complete**: Create copies of the templates in the specific feature folder
- **Maintain structure**: Respect the sections defined in the templates for project consistency

---

## 💰 Token and context management

### ⚠️ Warning about token consumption

The SPEC and PLAN creation process can consume a significant amount of tokens and context window.

### Recommendations to optimize consumption

1. **Separate by phases**: Create independent chats for each development phase
   - Chat 1: SPEC generation
   - Chat 2: PLAN generation (attach SPEC as reference)
   - Chat 3: Implementation (attach SPEC and PLAN as reference)

2. **Reuse documentation**: The generated SPEC and PLAN files are complete documents that can be attached in new chats
   - Avoids repeating all context in each conversation
   - Significantly reduces token consumption
   - Maintains coherence between phases

3. **Advantages of separate chats**:
   - Greater efficiency in token usage
   - Cleaner context focused on each phase
   - Lower risk of reaching context window limits
   - Better work organization

> **Tip**: When starting a new chat for implementation, attach the previously generated `spec.md` and `plan.md` files. This provides all necessary context without unnecessarily consuming the context window.
