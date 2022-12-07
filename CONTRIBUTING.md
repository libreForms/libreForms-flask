## How to contribute to libreForms

#### **Did you find a bug?**

* **Ensure the bug was not already reported** by searching on GitHub under [Issues](https://github.com/signebedi/libreForms/issues) with the \[bug\] tag.

* If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/signebedi/libreForms/issues/new). Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring. Make sure to use the \[bug\] tag

#### **Did you write a patch that fixes a bug?**

* Open a new GitHub pull request with the patch.

* Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.

#### **Did you fix whitespace, format code, or make a purely cosmetic patch?**

Changes that are solely cosmetic in nature and do not add anything substantial to the stability, functionality, or testability of libreForms will generally not be accepted.

#### **Do you intend to add a new feature or change an existing one?**

* Suggest your change under [Issues](https://github.com/signebedi/libreForms/issues) with the \[enhancement\] tag before making any pull requests.
* Ensure that any new scripts you add conform to the project's [standard boilerplate](https://github.com/signebedi/libreForms/issues/78).
* Ensure that any changes you've proposed to existing scripts include your name in the \_\_credits\_\_ list of that script.

#### **Do you have questions about the source code?**

* Ask any question about how to use libreForms under [Issues](https://github.com/signebedi/libreForms/issues) with the \[question\] tag.

#### **Do you want to contribute to the libreForms documentation?**

* Suggest your change under [Issues](https://github.com/signebedi/libreForms/issues) with the \[documentation\] tag before making any pull requests.

#### **Are there general approaches to how commits and PRs should be made?**

Git contribution messages should generally be prepended with the following conventions (with major conventions bolded):

- **Added**: a catch-all for additions to the code base
- **Removed**: dropping a significant component of an existing feature
- **Modified**: a modification to a current feature of the codebase
- **Fixed**: a broken feature or bug fix
- **Docs**: modified the codebase documentation
- **Tests**: modified the codebase tests
- Routine: clerical and minor changes or refactors not affecting the API
- Grumble: progress not yet sufficient to result in any changes above

Generally, contributors should aim to link all of their contributions to [Issues](https://github.com/signebedi/libreForms/issues) to help with code review. We'd appreciate if you'd append an issue number to the header of any contribution message. Here's an example of a commit message that would conform to these guidelines:

```
Added: standard boilerplate to app/signing.py (#78)

libreForms contributing guidelines generally require scripts to include standard boilerplate to explain the scripts functionality and any appropriate discussion of key decisions that were made. In addition, the guidelines require additional metadata variables. This contribution modifies app/signing.py to conform to these guidelines.
```

Thanks for your interest in the libreForms project.

signebedi
