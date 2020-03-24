# BlackboardQuizMaker

A python module which lets you conveniently create multiple choice and
numeric question pools on your own PC, containing LaTeX math and
embeded images, as a zip package which you can then import into
Blackboard.

Hopefully his will help you work around the limitations (and slow
performance) of the blackboard equation editor. It also allows you to
generate permutations of questions programmatically.

# Dependencies

This package requires a working installation of python, python-lxml,
and python-image, imagemagick, and LaTeX. You can install these on
ubuntu like so:

```
sudo apt-get install python-lxml python-image imagemagick 
```

# How to use it (python)
Create an instance of the Package class using the "with" pattern, add one or more Pools, then add questions to each pool!
```python
#This code snippet is taken from python_example.py
import BlackboardQuiz

#You need a package, which is what you'll eventually upload to
#Blackboard/MyAberdeen
with BlackboardQuiz.Package("EX3502_20") as package:

    #You may have multiple question pools in a single package, just
    #repeat this block with different pool names.
    with package.createPool('TestPool', description="<p>Description</p>", instructions="<p>Instructions</p>") as pool:
        #We can do numerical questions
        pool.addNumQ('Douglas Adams Question', 'What is the answer to life, the universe, and everything?', 42, erramt=0.1, positive_feedback="<p>Good, you have read well.</p>", negative_feedback="<p>Where have you been?</p>")

        #Or multiple choice questions
        pool.addMCQ('Shakespeare','To be, or not to be', answers=["<p>To be</p>", "<p>Not to be</p>", "<p>That is the question.</p>", "<p>Both.</p>"],  correct=2, positive_feedback="<p>Again, you have read well.</p>", negative_feedback="<p>Try reading Hamlet.</p>")

        #Maths can be included using latex
        pool.addMCQ('Math question', 'Please solve this "display" equation: $$\\int x\,dx=?$$',
                    answers=['$x$', '$\\frac{x^2}{2}$', '$gh$'],
                    correct=1,
                    positive_feedback="Well done!",
                    negative_feedback="Sorry, but the general rule for polynomial integration is $\\int x^n\\,dx=\\frac{x^{n+1}}{n+1}$ for $n\\neq -1$"
        )
        
        #Embedding external images is easy too and will automatically
        #be included into the package. Other HTML can also be used for
        #formatting, I don't check it.
        pool.addMCQ('HTML question', 'I cant believe that you can embed images! <img src="example_image.png"> Cool huh?',
                    ['Really cool.', 'Well, its not that impressive, its basic functionality.', 'Blackboard sucks.'],
                    correct=0)
```

# How the program works

Blackboard has an XML file format which it uses to upload/download
question sets or "pools" (or anything really). This file format lets
you also embed images and this is how the LaTeX support is
implemented. All strings are searched for `$` which are used to
indicate a LaTeX string. Each of these are rendered into a png using
the tex2im script included (matplotlib is an alternative technique but
I found it couldn't calculate correct bounding boxes). The resulting
png images are then directly embedded into the zip file and the
formulas are replaced by html img tags which link to these images.

The main difficulties I've faced is to reverse engineer how blackboard
attaches unique identifiers to files. This was figured out by "reverse
engineering" their file format (downloading a question set with an
embedded image in it and looking at the tags). There is a slight issue
with the current implementation in that it stores the images in a
ugly-named subdirectory of the course. I think this can be fixed by
adding additional xml tags but I'm not sure its worth the effort.
