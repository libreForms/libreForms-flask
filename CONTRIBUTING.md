## Contributing to libreForms-flask

This is an open source implementation of the [libreForms spec](https://github.com/libreForms/spec) in the Python [Flask framework](https://flask.palletsprojects.com/en/latest/). It depends on community contributions like bug reports & patches, enhancement requests, and new feature contributions.

#### What to do when you identify a potential bug

When you experience behavior that does not seem to conform to the application's expected behavior, you should first review the GitHub [Issues](https://github.com/libreForms/libreForms-flask/issues) and filter using the \[bug\] tag. If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/libreForms/libreForms-flask/issues/new). Be sure to include a **title and clear description**, as much relevant information as possible, a [stack trace](https://en.wikipedia.org/wiki/Stack_trace), and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring. Make sure to use the \[bug\] tag.

#### What to do when you patch a bug

Before submitting a patch as a GitHub pull request, please ensure that there is a corresponding issue for the bug, which includes preliminary discussion of the proposed fix. This is the first step of code review. When you open a pull request, pleae ensure its description clearly describes the problem and solution (see below for formatting guidelines).

As a rule, we will not accept pull requests that are not linked to an issue, or which do nothing but fix whitespace, format code, or make a purely cosmetic changes. In such cases, you should consider opening an issue to discuss the proposed change instead.

#### What to do when you modify or add a feature

If there is a new feature you would like to contribute, you should start by reviewing the Github issues to see if a discussion has already been opened.  
This is the best way to discuss proposed modifications, and understand how that might effect the codebase, before making them. Next, you should review the [project roadmap](https://github.com/libreForms/libreForms-flask/issues/39) to determine whether there is a planned application version under which your proposed fix would best fit. 

Any time you write add functionality in a new script, ensure that this script conforms to the project's [standard boilerplate](https://github.com/libreForms/libreForms-flask/issues/78). If you've proposed a change to existing scripts, add your name in the \_\_credits\_\_ list of that script - you've earned it!

#### What to do when you have questions about the source code

You should start by reviewing the [application documentation](https://libreforms.readthedocs.io/en/latest/), which may answer your question. You may also benefit from briefly reviewing the [specification](https://github.com/libreForms/spec) upon which this application is built. You should also search the Github issues and filter using the \[question\] tag. Lastly, all scripts in this application should include developer notes at the top of the scipt - you should consider looking there if you know which script your question concerns.

If these resources don't answer your questions, open a Github [Issue](https://github.com/libreForms/libreForms-flask/issues) with the \[question\] tag. It's likely that others will have the same question and benefit from the discussion.

#### How to make contributions to the application documentation

If you have notes you'd like included in the [application documentation](https://libreforms.readthedocs.io/en/latest/), start by suggesting your change under the Github [Issues](https://github.com/libreForms/libreForms-flask/issues) with the \[documentation\] tag before making any pull requests. Note that admin and user documentation are stored in a [separate repository](https://github.com/libreForms/libreForms-flask-docs), but you can feel free to add issues to this repository so long as they are appropriately tagged.

#### How to structure pull requests

Git contribution messages should generally be prepended with the following conventions:

- **Added**: added a new feature
- **Removed**: deprecated or removed a component of an existing feature
- **Modified**: modified an existing feature
- **Fixed**: addressed a broken feature or bug fix
- **Docs**: added or modified code documentation
- **Tests**: added or modified test functionality

Generally, contributors should aim to link all of their contributions to [Issues](https://github.com/libreForms/libreForms-flask/issues) to help with code review and facilitate discussion. We'd appreciate if you'd append an issue number to the header of any contribution message. Here's an example of a commit message that would conform to these guidelines:

```
Added: standard boilerplate to app.signing (#78)
```

Thanks for your interest in libreForms-flask.

signebedi
