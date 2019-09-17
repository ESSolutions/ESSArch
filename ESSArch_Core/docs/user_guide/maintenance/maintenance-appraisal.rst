.. _maintenance-appraisal:

*********
Appraisal
*********

The main function of the appraisal page is creating appraisal rules that
run jubs automatically or manually on selected content in the archive.

Create appraisal rule
=====================

To create a new appraisal rule click **Create** aprpaisal rule list.

Enter a name for the new appraisal rule, when it should be run and selected
target files.

**Frequency** decides how often a rule should be executed and is specified
with **cron** syntax. For example: ``0 15 * * 3`` means every wednesday at
15 o' clock.

To add a **Path** type for example **/*.docx in the **Path** field and
click the **+** button. If the whole AIP should be affected by the appraisal
leave this field empty.

Connect rule to AIP
===================

Enter the **Access/Storage units** page, mark one or more AIP(s), right click
one of them and select **Appraisal** and a list of the selected AIPs appears.
Every row can be expanded to see connected appraisal rules for the
specific AIP. We also get a button for adding new rules to AIPs.

Appraisal job lists
===================

Under the list of appraisal rules there are three more list views containing
appraisal jobs filtered by states **Ongoing**, **Next** and **Finished**.
The **Ongoing**  list shows jobs that are currently running, the **Next**
list shows jobs that will be run automatically in execution order and the
**Finished** list shows jobs that are finished.

In the **Next** list the appraisal job can be previewed by clicking
the **Preview** button.

When a rule is connected to at least on AIP, jobs will be created and visible
in the **next** list. The job will be executed at the given **start** time,
except if the user wants to start the job before the given time.
A job in the **Next** list can be started manually by clicking **Preview**
and then **Run**. The job will then be moved to the **Ongoing** list and finally to the **Finished** list.

In the **Finished** a user can see the appraisal report for the finished
job by clicking  **report**.
