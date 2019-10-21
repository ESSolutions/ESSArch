.. _maintenance-conversion:

*****************
Format conversion
*****************

The format conversion pages main function is to allow the user to create
converison jobs that run automatically or manually on selected content
in the archive.

Create conversion rule
======================

To create a new rule click the **Create**-button over the appraisal rule list.

Enter a name for the new conversion rule, select interval for automatic jobs
or select the **Run manually** option if the rule should be triggered manually and
what files should be converted in the connected AIPs.

**Frequency** decides how often a rule should be executed and is specified
with **cron** syntax. For example: ``0 15 * * 3`` means every wednesday at
15 o' clock.

To add a **Specification** type for example ``**/*.docx`` in the **Path**
field, **pdf** in the **target** field and **Libreoffice** in the **Tool**
field, then click the **+**-button.
This rule will convert all .docx-files to .pdf using libreoffice.

Connect rule to AIP
===================

Enter the **Access/Storage units** page, mark one or more AIP(s), right click
one of them and select **Conversion** and a list of the selected AIPs appears.
Every row can be expanded to see connected conversion rules for the
specific AIP. We also get a button for adding new rules to AIPs.

Conversion job lists
====================

Under the list of conversion rules there are three more list views containing
conversion jobs filtered by states **Ongoing**, **Next** and **Finished**.
The **Ongoing**  list shows jobs that are currently running, the **Next**
list shows jobs that will be run automatically in execution order and the
**Finished** list shows jobs that are finished.

In the **Next** list the converison job can be previewed by clicking
the **Preview** button.

When a rule is connected to at least on AIP, jobs will be created and visible
in the **next** list. The job will be executed at the given **start** time,
except if the user wants to start the job before the given time.
A job in the **Next** list can be started manually by clicking **Preview**
and then **Run**. The job will then be moved to the **Ongoing** list and finally to the **Finished** list.

In the **Finished** a user can see the conversion report for the finished
job by clicking  **report**.
