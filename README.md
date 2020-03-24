# BlackboardQuizMaker

A python module which lets you conveniently create multiple choice
question pools locally, containing LaTeX math and embeded images, as a
zip package which you can then import into Blackboard.

Hopefully this will help you work around the limitations (and slow
performance) of the blackboard equation editor.

# Dependencies

This package requires a working installation of python, python-lxml,
and python-image, imagemagick, and LaTeX. You can install these on
ubuntu like so:

```
sudo apt-get install python-lxml python-image imagemagick 
```

# How to use it (python)
Simply create an instance of the quiz class using the "with" pattern, and add questions!
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

Note, you can embed html into the questions as well (such as for line
breaks or other formatting).

# How to use it via a csv file

To be honest, the python interface is a bit clunky for writing
questions in (although its the most customisable). I like to write all
the questions into a csv file and have a tool to convert this into the
required blackboard zip format. This is quite easy to put together
using Blackboard: taking a look at csv_reader.py:

```python
#This code snippet is taken from csv_parser.py
import BlackboardQuiz
import csv
import sys
from random import shuffle

if len(sys.argv) < 3:
    print "Usage: csv_parser.py course_ID pool_1.csv [pool_2.csv ...]"
    print " output is in course_ID.zip"
    print "  Each line of pool_X.csv should have the following structure"
    print '  "Question", "Correct answer", "Incorrect answer 1","Incorrect answer 2",...'
    exit()

import os
with BlackboardQuiz.Package(sys.argv[1]) as package:
    for csv_file_name in sys.argv[2:]:
        if csv_file_name[-4:] != '.csv':
            raise Exception("File "+csv_file_name+" does not end in .csv!")

        pool_name = os.path.basename(csv_file_name)[:-4]
        with open(csv_file_name,'rb') as csvfile, package.createPool(pool_name) as pool:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"', skipinitialspace=True)
            for row in reader:
                if len(row) == 0:
                    continue
                if row[0] == "":
                    raise Exception("Blank question!")

                #Get rid of any blank answers
                row = filter(None, row)
                
                #Shuffle the answers
                answer_idxs = list(range(1, len(row)))
                shuffle(answer_idxs)
                answers = map(lambda x : row[x], answer_idxs)
                pool.addQuestion(row[0], answers, correct=answer_idxs.index(1)+1)
```

Now I can just make a file (called MyQuiz.csv) which contains a line
for each question, followed by the correct answer, and as many
incorrect answers as I like. For example:

```
"Convert $\vec{a}+\vec{b}$ to index notation.", "$a_k+b_k$", "$a_i+a_i$", "$a_i+b_j$"
```

Then I can run `./csv_reader.py COURSE_CODE MyQuiz.csv` and it will give me a
question pool called "MyQuiz" in COURSE_CODE.zip with all the rendered
latex formula included!

# How the program works

Blackboard has an XML file format which it uses to upload/download
question sets or "pools" (or anything really). This file format lets
you also embed images and this is how the LaTeX support is
implemented. All strings are searched for `$` which are used to
indicate a LaTeX string. Each of these are rendered into a png using
the tex2im script included (matplotlib couldn't calculate correct
bounding boxes). The resulting png images are then directly embedded
into the zip file and the formulas are replaced by html img tags which
link to these images.

The main trick was to reverse engineer how blackboard attaches unique
identifiers to files. This was figured out by "reverse engineering"
their file format (downloading a question set with an embedded image
in it and looking at the tags). There is a slight issue with the
current implementation in that it stores the images in a ugly-named
subdirectory of the course. I think this can be fixed by adding
additional xml tags but I'm not sure its worth the effort.

The basic question structure was reverse engineered from the question
generator here: http://www.csi.edu/blackboard/bbquiz/
