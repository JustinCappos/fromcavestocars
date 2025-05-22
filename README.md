# From Caves To Cars

Hello world!

This is an experiment I'm doing to really understand how well OpenAI works at complex tasks.  I also don't have much direct experience with Github Actions, CI/CD pipeline deployments, Flask/Jinja2, Web frontends (CSS/Javascript), etc. and this is a chance for me to get some hands-on experience.

**I am asserting strongly that what I've doing here is neither secure, nor a recommended way to do things!**   What I'm trying to do is push OpenAI automation as far as possible into all aspects of a simple software project.  In a perfect world, eventually OpenAI would completely run this project in a fully automated way.  Of course, I don't expect that to be feasible, so I'm using this project to understand how and where it falls apart.

## What is "From Caves To Cars"?
This is a very simple educational game that has someone starting with things that existed in caveman times, build their way up to modern devices (such as a pencil, a linen tablecloth, or an automobile).  For example one might use a stone as a hammer on flint to shape a primitive knife, etc. and slowly build the materials and tools needed to build the goal.

Note that all of the descriptions about how to make things come from asking OpenAI how to make these items.  So, the content here also comes from LLM queries.  Also, the code (especially the frontend, Flask, etc. code) was at least initially attempted by OpenAI / Copilot.  It's probably more accurate to say this was AI assisted coding by me (or maybe I helped the AI?).  The early code (around data retrieval from OpenAI) was more hand generated after struggling with getting LLM generated code to work, where as later code (frontend, etc.) was much more AI generated.  

## How I envision OpenAI managing this project
My idea is to try to have the application manage itself.  To do this, the application will receive notifications from Github when a Github issue is opened.  The application will use OpenAI to prepare a PR that attempts to fix the Github issue.  This PR will be tested by a Github action and the application will see and summarize the result of the PR in a comment in the issue.  If the PR fails the test suite, the application will retry (a limited number of times), taking information from the test failure(s) into its next attempt to make a PR. If the tests pass, the PR should be merged and the application should be restarted with the changes.  

Of course, I cannot open the ability to request code generation via issues up to anyone to create issues for security / spam reasons.  I will manually tag issues that I want it to run on for now.

Note, that after thinking this over and talking about this with Ingy and Aditya, I'm going to separate out this functionality in https://github.com/DevBotJr   If this works well, this will be a generally useful tool for others.

Note: I may back up the user and other databases periodically, but don't expect this to be a production service which works well.  This is meant more as a toy to learn about LLM capabilities / limitations.

If you find a security problem here, please email jcappos@nyu.edu.  Since this doesn't have any sensitive data and no one is using this in production for anything, I'm not going to ask you to bother with GPG signing, etc.

## What is here?
Most of the files have a comment block at the top or are only a few lines.  However, to run this, you need to set up a bunch of environment variables with your API keys.  You also would need to copy everything in examplefiles/ to the root directory of the project. 

Note that this design was done by a mix of just going where the LLM took me and me steering it in reasonable directions.  So it has a really weird mix of json files, databases, etc.  It also assumes that there is persistent state (see userstatedict and the local database files).   This all will need to be converted over to run in a stateless manner in the cloud.
