Pacifica Enterprise UI

Purpose



Create professional, reliable and premium enterprise interfaces for Pacifica Produce.



The system manages invoices, credits, balances, reconciliations, account statements, receiving documents and check registration.



The interface must feel precise, organized, efficient and trustworthy. Prioritize data clarity and workflow efficiency over decoration.



Technology baseline

Fields, menus, calendars and buttons: Angular Material.

Advanced tables and controls: Kendo UI for Angular or Angular CDK.

Custom visual styling: SCSS/CSS.

Icons: Material Icons first; custom SVG only when justified.

Theme: CSS variables plus Angular Material/Kendo theme.

Compilation: Angular CLI and TypeScript.

Reuse existing dependencies before adding new ones.

Do not introduce a library without a clear technical benefit.

Visual direction

Create premium B2B financial interfaces.

Use deep teal, ink blue, warm white, soft gray, green, amber and red.

Use restrained and professional colors.

Avoid generic gradients, neon colors and excessive decoration.

Avoid excessive rounded cards and unnecessary containers.

Use shadows only to establish hierarchy.

Keep layouts compact but breathable.

Every visual element must serve navigation, hierarchy or feedback.

Do not leave accidental white space.

Do not make every section look like a separate card.

Design tokens



Use reusable variables instead of isolated values.



Ink: 

\#123B57

Teal: 

\#0E7079

Soft background: 

\#F7FAF8

Border: 

\#DCE8E2

Body text: 

\#526675

Success: 

\#187C4A

Warning: 

\#CA8A04

Error: 

\#B42318

Small spacing: 4px

Compact spacing: 8px

Standard spacing: 12px and 16px

Section spacing: 24px

Large spacing: 32px

Design reasoning process



Before implementing a new feature:



Understand the user goal and business workflow.

Identify the primary action and secondary actions.

Determine which information is essential or auxiliary.

Choose the correct structure: table, form, modal, drawer, tabs, KPI or chart.

Consider administrator and customer roles.

Consider loading, empty, error, success and disabled states.

Consider Spanish and English text length.

Consider desktop and smaller screen behavior.

For complex changes, propose the layout and interaction before coding.

Implement only after the design decision is clear.

Button hierarchy

Use one primary action per section.

Give secondary actions less visual weight.

Use destructive styling only for irreversible actions.

Use icon-only buttons only when the meaning is obvious.

Icon-only buttons require an accessible label or tooltip.

Keep button height, padding and alignment consistent.

Group related actions together.

Separate destructive actions from normal actions.

Never allow buttons to overlap, disappear or wrap unexpectedly.

Table standards

Tables must use all available width.

Do not force large desktop min-width values unnecessarily.

Enable horizontal scroll only when readable columns cannot fit.

Column widths must be intentional and add up to the available space.

Keep headers aligned with their data.

Use ellipsis only where truncation is acceptable.

Align currency and numeric values consistently.

Use one consistent date format.

Use semantic colors for Paid, Pending, Overdue, Duplicate and Error.

Action columns must adapt to the number of available buttons.

Keep action buttons visible and properly spaced.

Do not hide essential data to solve responsive problems.

Include loading, empty and error states.

Verify tables with realistic long names and large amounts.

Verify both administrator and customer layouts.

Chart standards

Use line charts for trends over time.

Use bar charts for customer or category comparisons.

Use stacked bars for composition.

Use KPI blocks for single summary values.

Avoid 3D charts and unnecessary decoration.

Use no more than five colors per chart.

Use semantic colors consistently.

Display currency with symbol and decimals.

Include meaningful titles, labels, tooltips and empty states.

Keep charts readable on smaller screens.

Forms and interaction

Group related fields logically.

Use clear labels and useful placeholders.

Validate required fields before submission.

Show errors near the affected field.

Disable actions while processing.

Preserve entered values when validation fails.

Move focus logically through sequential fields.

Close menus and popovers when clicking outside.

Do not show customer-dependent data before the required customer is selected.

Make irreversible actions require confirmation.

Responsive behavior

Use desktop space efficiently.

Adapt columns before enabling scroll.

Keep important information visible.

Reduce spacing before hiding data.

Use scroll only when the content genuinely exceeds the viewport.

Verify wide desktop, normal desktop and narrow layouts.

Do not create different visual rules for administrator and customer without a product reason.

Accessibility and localization

Every interactive control must be keyboard accessible.

Use visible focus states.

Provide accessible labels for icon-only buttons.

Maintain sufficient text and background contrast.

Do not rely on color alone to communicate status.

Keep Spanish and English labels consistent.

Allow for longer translated labels without breaking layouts.

Implementation rules

Inspect existing components and styles before creating new ones.

Prefer reusable components and CSS classes.

Avoid duplicated inline styles.

Keep business logic separate from presentation logic.

Use descriptive names.

Avoid premature abstractions.

Do not add dependencies without justification.

Keep changes focused and maintainable.

Run the Angular build before delivery.

Do not publish changes to Oracle without explicit authorization.

Visual quality gate



Before delivering any UI change:



Check for accidental white space.

Check for overlapping or clipped controls.

Check that tables use the available width.

Check that scroll appears only when necessary.

Check typography hierarchy and contrast.

Check loading, empty, error and success states.

Check administrator and customer views.

Check Spanish and English.

Test with realistic data.

Run the build successfully.

Explain any remaining visual tradeoff honestly.

Established design decisions



These decisions have already been made and must not be re-proposed or reconsidered without explicit authorization.



Interaction patterns

Simple confirmations: inline confirm, not modal dialogs.

Filters: chips or inline controls, not tabs.

Success feedback: inline alert or status indicator, not MatSnackBar.

Errors: inline message near the affected field or section, not a global toast.

Irreversible actions: always require an explicit confirmation step.

Layout patterns

Invoice, credit and balance tables always show customer, amount and status as visible columns without horizontal scroll on desktop.

Do not wrap each section in a card unless it represents a genuinely independent unit.

Do not add decorative dividers between fields inside the same form group.

KPI blocks go at the top of summary views, above tables and charts.

Component decisions

Do not create a new component if an existing one can be extended or configured.

Do not introduce a new library if Angular Material or Kendo UI already covers the need.

Shared components live in the shared module. Page-specific components stay in their feature module.

Quality reference



When in doubt about the expected standard, use these existing implementations as reference.



If you do not have access to these files, ask before assuming a standard.



Well-implemented table: look for the invoice list component in the invoices feature module.

Well-implemented form: look for the credit form component in the credits feature module.

Well-implemented KPI section: look for the dashboard summary section.

Well-implemented status badge: look for the shared status-badge component.



Use these as the baseline for naming, structure, spacing and interaction patterns. If a new component you are building is similar to one of these, match its structure before adding anything new.



When in doubt



Apply these rules in order when the right decision is not obvious.



Prefer the simpler solution over the more elegant or technically interesting one.

Prefer consistency with what already exists over introducing something new.

Ask before creating a new component, pattern or dependency.

Ask before removing any existing behavior, even if it seems redundant.

Do not assume a business rule. If the requirement is ambiguous, stop and ask.

Do not solve a layout problem by hiding data. Find a layout that fits the data.

If two valid approaches exist, briefly describe both and let the team decide.



When uncertain about a visual decision, describe what you see as the options and the tradeoff, then wait for direction before implementing.

