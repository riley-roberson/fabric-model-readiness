# Power BI Standards / Best Practices

> **This is the authoritative standards document.** When Scout rules or Enforcer proposals conflict with these standards, defer to this document. These standards apply to all semantic models analyzed by the system.

## Outline

- Data Modeling
- Power Query
- DAX
- Reports and Dashboards
- Project Management
- Security and Sharing
- Deployment and Administration

---

## Data Modeling

### General

- Create centralized "Golden Datasets" instead of separate datasets for specific reports.
- Only pull in the years of data that you are going to analyze.
- Do not pull in columns that you are not going to use.
- All data that needs to be consumed in Power BI should be brought into Azure and modeled to ensure proper controls, speed, and data quality.
- Avoid float data types unless necessary.

### Star Schemas

- Store shared datasets in a separate workspace dedicated to shared datasets without any reports.
- All models should be designed as star schemas instead of flat tables or snowflakes. Bring snowflakes into one dimension, even if it creates storage inefficiencies.
- Avoid bi-directional and many-to-many relationships when possible. If you are able, denormalize the relationships to create a star schema.
- Many-to-many relationships should be single direction.
- Create model views for each star and organize by Agile Data Warehouse Design (ADWD) order.

### Fact Tables

- Fact tables should only include fact columns and surrogate keys.
- Fact tables should be hidden from the users. Occasionally, the use of degenerate dimensions is permitted. When used, you can expose these fields to the user.
- In order to connect two different fact tables, they must both conform to shared dimension tables (i.e. shared geography and date tables). Reuse central conformed dimensions from other models whenever possible.
- Do not include the fact table key in the model unless necessary.
- Mark primary keys.

### Dimension Tables

- Unless necessary, do not replicate dimension tables for tables with multiple possible relationships. Instead, use active and inactive relationships and the DAX measure `USERELATIONSHIP`.
- Dimension tables should consist of a surrogate key and appropriate dimension columns.
- Hide the surrogate key from the user.
- Group columns in display folders to make it easier for the user to find what they are looking for.
- Mark primary keys.
- Sort text columns based on relevant numerical columns.
- Reduce usage of long-length columns with high cardinality.

### Dates

- Dates can occur in a dimension or fact table. The date should sit in the table where it is describing the specific data. If the date is describing the fact, it goes in the fact table. If it is describing an attribute of a dimension, it goes in the dimension table. Dates can be denormalized into the fact table to tie to the date table.
- Date columns (i.e. event_date, order_date, etc.) can serve as foreign keys to the date dimension table.
- Use a date table for time intelligence calculations.
- Mark calendar table as date table.
- If possible use one date table if there are multiple date fields and use the function `USERELATIONSHIP` instead of creating additional date tables.
- Turn off auto generate date tables in settings.
- Split datetime columns into separate date and time columns.

### Development

- Limit the data that you pull into the local PBIX file by configuring an incremental refresh policy or parameters for development.
- Unless you have a really good reason for using DirectQuery, you should use the Import/Vertipaq connection type.
- Turn off default aggregations.
- Use external tools like ALM Toolkit, SSMS, and Tabular Editor to create new measures and refresh single tables.

---

## Power Query

- The dataset should pull in production ready tables from Azure via import method.
- Push transformations as far back to the source if possible. In an ideal scenario, you should be pulling in production ready tables from Azure into Power BI.
- Ensure that your Power Query steps do not break query folding.
- Always format your M code using: Power Query Formatter.
- Rename variables/applied steps to make the purpose of your transformations more clear.
- Comment your code if necessary.
- Group tables in the following folders: Dimension Tables, Fact Tables, Measure Tables, Parameters, RLS Tables, Staging Tables, Intermediate Tables, Reference, and Functions.
- Prefix all function names with `fnc` and use camel case.
- Remove unnecessary steps.
- Future proof your code.

---

## DAX

- Always test measure performance.
- DAX should be written to balance performance and readability.
- Create base DAX measures that will be stored within centralized model in order to maintain shared definitions of calculations.
- Store all measures in measure tables and create an empty measures table for local measures to be stored.
- Group measures in display folders to make it easier for the user to find what they are looking for.
- Add measure formulas and an explanation of what the measure does in the column definition section.
- No two measures should have the same definition.
- Measures should not be direct references of other measures.
- Use measure branching instead of redefining measure components multiple times.
- Format all measures using DAX Formatter by SQLBI. Both long and short formatting options are acceptable.
- Do not use default aggregations -- explicitly define summary aggregations as measures.
- Only use single quotes for table name if it is required and omit single quotes if table name has no spaces.
- Never use table names (not fully qualified) for measures: i.e. `[my_measure]`.
- Always use table names (fully qualified) for column references: i.e. `'my_table'[my_column]`.
- Make use of variables to break out complex DAX statements.
- Use longer, more descriptive variable names than short names.
- When using variables, your return statement should only be a variable reference with no additional transformations.
- Name all variables using snake case and a leading underscore: i.e. `VAR _snake_case`.
- Comment the code when needed.
- Name all temporary calculated columns using snake case and a leading `@` symbol: i.e. `[@temporary_column]`.
- Use calculation groups instead of several variations of the same calculation in different measures.
- Instead of creating columns in `SUMMARIZE`, use `SUMMARIZE` and `ADDCOLUMNS` together.
- Never use shortened `CALCULATE` syntax: i.e. don't use `[measure](filter)` but `CALCULATE( [measure], filter )`.
- Use the formula `CROSSFILTER` instead of creating bidirectional relationships.
- Use the `DIVIDE` function for division.
- Avoid using the `IFERROR` function.
- Use `SWITCH TRUE` instead of nested `IF` statements.

---

## Reports and Dashboards

- Use wireframe template for all new report creation.
- Leverage published, shared datasets to ensure everyone is using the same source of truth.
- Set up dedicated workspaces for reports that are separate from the datasets.
- Never forget the purpose of the report. You are trying to communicate the story of the data to the user. Every choice made should be intentional. Design for a target.
- Use features like tooltips, bookmarks, buttons, etc. to improve the UI and UX.
- Use the company's JSON theme file to define default color themes and fonts for reports, as well as include current licenses for custom visuals.
- Develop standard report templates and use them for new reports instead of creating reports from scratch.
- Develop a mobile phone view for all reports.
- To help determine which chart to use, refer to Power BI Visuals Reference (SQLBI).
- For dashboards, keep everything at a glance.
- Keep it simple. Remove unnecessary elements and do not clutter the page.
- Align elements.
- Highlight the most relevant information.
- Be clear.
- Start all axes from zero.
- Shorten the numbers when possible.
- Choose the right colors. Only use color purposely, otherwise, use black, white and grey.
- For dashboards, design dashboards, not reports.
- Show variations.
- Leave the noise off.
- Include a help and information page for all reports.

---

## Project Management

- For BI modeling projects, use the BI Project template.
- Use wireframe template for all new report requests.
- Use Teams for agile, quick conversations for BI projects.
- Be proactive in communication with stakeholders.
- Be proactive in preparing for projects.
- Use UAT testing sheet for testing data models and reports for BI projects. Regularly check items assigned to you.

---

## Security and Sharing

- Give the minimum amount of access necessary to a user.
- Define at least two RLS roles: Admin and General. Avoid too many security roles for a dataset / semantic model.
- The Admin role should have no filters and the General role should have all filters applied.
- Dataset / semantic model permissions should distinguish between read and read/build permissions.
- Only AAD groups should be granted permissions to an RLS role.
- Use dynamic row level security, object level security, or data masking if the data is sensitive.
- Avoid using OLS if possible. If you need to hide an entire table from a role, hide every row.
- Store reports in a centralized shared drive separate from reports: i.e. SharePoint.
- Share apps with users instead of individual reports when possible.
- Share apps/reports with AAD groups instead of individuals when possible.
- Share datasets and reports with AAD security groups instead of individuals.
- Only developers should be granted access to workspaces, only share content via apps or direct sharing.
- Create short URLs for each report.

---

## Deployment and Administration

- Employ at least two Power BI workspaces for semantic models: dev and prod. Another environment may be helpful if we envision the need for a more stable environment than dev to test model performance.
- Use ALM Toolkit to review and publish changes to existing semantic models. Minimize publishing changes to partitions and roles, unless changes require updates.
- Utilize the `.pbit` file to create new datasets / semantic models, which includes many of the above standards for Power Query and development parameters.
- Provide build permissions to semantic models using AAD groups that match the appropriate security roles implemented for each model.
- Review tenant settings annually.
