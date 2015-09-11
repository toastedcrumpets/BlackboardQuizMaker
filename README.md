# BlackboardQuizMaker
A python module which lets you create multiple choice question pools with LaTeX math expressions, and upload them to Blackboard. Even images can be included with some tweaks

# Dependencies
This needs python, python-lxml, and python-matplotlib.

# How to use
Simply create an instance of the quiz class using the "with" pattern, and add questions!
```
import BlackboardQuiz

with BlackboardQuiz.Quiz("Index notation questions") as quiz:
    quiz.addQuestion('What is the following in index notation?<br/> $\\vec{a}+\\vec{b}$', ['$a_k+b_k$', '$a_i+a_i$', '$a_i+b_j$'], 1)
```
Note, you can embed html in the questions as well, to give you line breaks or other formatting. You can even embed external images if you want to.
# How it works
Blackboard has an XML file format which it uses to upload/download question sets or "pools". This file format lets you also send images and this is how the LaTeX support is implemented. All strings are searched for $$ which indicate a LaTeX string, then these are rendered using Matplotlib. The resulting png images are then embedded in the zip and the $$ tags are replaced by links to these images.

This was figured out by reverse engineering their file format, and the question generator here: http://www.csi.edu/blackboard/bbquiz/
