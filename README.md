# BlackboardQuizMaker
A python module which lets you create multiple choice question pools with LaTeX math expressions, and upload them to Blackboard. Even images can be included with some tweaks

# Dependencies
This needs python, python-lxml, and python-matplotlib.

# How to use
Simply create an instance of the quiz class using the "with" pattern, and add questions!
```
#!/usr/bin/env python

import BlackboardQuiz

with BlackboardQuiz.Quiz("Index notation questions") as quiz:
    quiz.addQuestion('What is the following in index notation?<br/> $\\vec{a}+\\vec{b}$',
                     ['$a_k+b_k$', '$a_i+a_i$', '$a_i+b_j$'],
                     correct=1)
    #Note that correct answer here is from 1 to 3 (not zero indexed)

    #You can also set the feedback using positive_feedback and
    #negative_feedback which can also contain images or latex
    quiz.addQuestion('$\\int x\,dx=?$',
                     ['$x$', '$\\frac{x^2}{2}$'],
                     correct=2,
                     positive_feedback="Well done!",
                     negative_feedback="Sorry, but the rule for integration is $\\int x^n\\,dx=\\frac{x^{n+1}}{n+1}$ for $n\\neq -1$"
    )
    
    #Embedding external images is easy too
    img_tag = quiz.embed_image('example_image.png')    
    quiz.addQuestion('I cant believe that you can embed images!'+img_tag+' Cool huh?',
                     ['Really cool', 'Well, its not that impressive, its basic functionality', 'Blackboard sucks'],
                     correct=1)

```
Note, you can embed html in the questions as well, to give you line breaks or other formatting. You can even embed external images if you want to.
# How it works
Blackboard has an XML file format which it uses to upload/download question sets or "pools". This file format lets you also send images and this is how the LaTeX support is implemented. All strings are searched for $$ which indicate a LaTeX string, then these are rendered using Matplotlib. The resulting png images are then embedded in the zip and the $$ tags are replaced by links to these images.

This was figured out by reverse engineering their file format, and the question generator here: http://www.csi.edu/blackboard/bbquiz/
