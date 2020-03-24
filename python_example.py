#!/usr/bin/env python

import BlackboardQuiz

with BlackboardQuiz.Package("EX3502_20") as package:
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
        

