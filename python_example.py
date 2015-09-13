#!/usr/bin/env python

import BlackboardQuiz

with BlackboardQuiz.Package("MyBlackboardPackage") as package:
    with package.createPool('Index notation questions') as pool:
        pool.addQuestion('What is the following in index notation?<br/> $\\vec{a}+\\vec{b}$',
                         ['The correct answer is $a_k+b_k$', '$a_i+a_i$', '$a_i+b_j$'],
                         correct=1)
        #Note that correct answer here is from 1 to 3 (not zero indexed)

        #You can also set the feedback using positive_feedback and
        #negative_feedback which can also contain images or latex
        pool.addQuestion('This is a display equation: $$\\int x\,dx=?$$',
                         ['$x$', '$\\frac{x^2}{2}$', '$gh$'],
                         correct=2,
                         positive_feedback="Well done!",
                         negative_feedback="Sorry, but the rule for integration is $\\int x^n\\,dx=\\frac{x^{n+1}}{n+1}$ for $n\\neq -1$"
                     )
    
        #Embedding external images is easy too
        pool.addQuestion('I cant believe that you can embed images! <img src="example_image.png"> Cool huh?',
                         ['Really cool', 'Well, its not that impressive, its basic functionality', 'Blackboard sucks'],
                         correct=1)
        
