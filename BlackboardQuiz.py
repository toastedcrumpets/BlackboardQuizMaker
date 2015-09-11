#!/usr/bin/env python

from lxml import etree
import time
import zipfile

import matplotlib.pyplot as plt
from cStringIO import StringIO

class Quiz:
    def __init__(self, quizname, description_text="Created by BlackboardQuiz!", useLaTeX=False):
        """Initialises a quiz
        """
        self.quizname = quizname
        try:
            import zlib
            compression = zipfile.ZIP_DEFLATED
        except:
            compression = zipfile.ZIP_STORED
        self.zf = zipfile.ZipFile(self.quizname+'.zip', mode='w', compression=compression)
        self.resource_counter = 1000000
        self.equation_counter = 0

        #Create the question datafile
        self.pool = etree.Element("POOL")
        etree.SubElement(self.pool, 'COURSEID', {'value':'IMPORT'})
        etree.SubElement(self.pool, 'TITLE', {'value':self.quizname})
        description = etree.SubElement(self.pool, 'DESCRIPTION')
        etree.SubElement(description, 'TEXT').text = description_text
        self.addDates(self.pool)
        self.questionlist = etree.SubElement(self.pool, 'QUESTIONLIST')
        self.question_counter = 0

        #Create the manifest file
        self.manifest = etree.Element("manifest", {'identifier':'man00001'})
        organisation = etree.SubElement(self.manifest, "organization", {'default':'toc00001'})
        etree.SubElement(organisation, 'tableofcontents', {'identifier':'toc00001'})
        resources = etree.SubElement(self.manifest, 'resources')
        resource = etree.SubElement(resources, 'resource', {'baseurl':"res00001", 'file':"res00001.dat", 'identifier':"res00001", 'type':"assessment/x-bb-pool"})

        if useLaTeX:
            #Use latex (not mathtex) for better but slower results
            from matplotlib import rc
            rc('text', usetex=True)

    def close(self):
        self.zf.writestr('imsmanifest.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.manifest, pretty_print=True))
        self.zf.writestr('res00001.dat', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.pool, pretty_print=True))
        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        
    def addfile(self, name, content):
        """Adds a file (given a name and content) to the quiz and returns the unique id of the file
        """
        self.resource_counter += 1
        name = name.split('.')
        self.zf.writestr('csfiles/home_dir/'+self.quizname+'/'+name[0]+'__xid-'+str(self.resource_counter)+'_1.'+name[1], content)
        return str(self.resource_counter)+'_1'


    def render_latex(self, formula, fontsize=12, dpi=120, format_='png'):
        """Renders LaTeX expression into an image data.
        """
        fig = plt.figure()
        text = fig.text(0, 0, u'${}$'.format(formula), fontsize=fontsize)
        #Fake render to force matplotlib to determine the actual size of the text
        buffer_ = StringIO()
        fig.savefig(buffer_, dpi=dpi, format=format_, transparent=True)

        #Determine the actual size of the text
        bbox = text.get_window_extent()
        width, height = bbox.size / float(dpi) + 0.005
        # Adjust the figure size so it can hold the entire text.
        fig.set_size_inches((width, height))

        # Adjust text's vertical position.
        dy = (bbox.ymin/float(dpi))/height
        text.set_position((0, -dy))

        #Now render the text again but with correct clipping
        buffer_ = StringIO()
        fig.savefig(buffer_, dpi=dpi, format=format_, transparent=True)
        return buffer_.getvalue()

    def embed_image(self, filename, img_data=None, attrib={'style':'display:block; margin-left:auto; margin-right:auto;'}):
        """Embeds image data or a file, and returns an img tag.
        """
        if img_data == None:
            with open(filename, mode='rb') as file:
                img_data = file.read()

        output = '<img src="@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-'+self.addfile(filename, img_data)+'"'
        for key, value in attrib.items():
            output += " "+key+'="'+value+'"'
        output += '>'
        return output
        
    def embed_latex(self, formula, attrib={}):
        """Renders a LaTeX formula to an image, embeds the image in the quiz
        and returns a img tag which can be used in the text of a
        question or answer.
        """
        name = "eq"+str(self.equation_counter)+".png"
        self.equation_counter += 1
        return self.embed_image(name, self.render_latex(formula), attrib=attrib)

    def process_latex(self, in_string):
        """Scan a string for LaTeX equations and process them.
        """
        #First, process the display equations
        in_string = in_string.split('$$')
        for i in range(1, len(in_string), 2):
            in_string[i] = self.embed_latex(in_string[i], attrib={'style':'display:block;margin-left:auto;margin-right:auto;'})
        in_string = ''.join(in_string)

        in_string = in_string.split('$')
        for i in range(1, len(in_string), 2):
            in_string[i] = self.embed_latex(in_string[i], attrib={'style':'vertical-align:middle'})
        in_string = ''.join(in_string)

        return in_string

    def addDates(self, element):
        """Helper function to add the DATES section
        """
        dates = etree.SubElement(element, 'DATES')
        etree.SubElement(dates, 'CREATED', {'value':time.strftime('%Y-%m-%d %H:%M:%SZ')})
        etree.SubElement(dates, 'UPDATED', {'value':time.strftime('%Y-%m-%d %H:%M:%SZ')})
    
    def addQuestion(self, text, answers, correct, positive_feedback="Good work", negative_feedback="That's not correct"):
        self.question_counter += 1 
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        etree.SubElement(self.questionlist, 'QUESTION', {'id':question_id, 'class':'QUESTION_MULTIPLECHOICE'})
        #Add the actual question node
        q_node = etree.SubElement(self.pool, 'QUESTION_MULTIPLECHOICE', {'id':question_id})
        self.addDates(q_node)
        body = etree.SubElement(q_node, 'BODY')
        etree.SubElement(body, 'TEXT').text = self.process_latex(text)
        flags = etree.SubElement(body, 'FLAGS', {'value':'true'})
        etree.SubElement(flags, 'ISHTML', {'value':'true'})
        etree.SubElement(flags, 'ISNEWLINELITERAL')
        
        a_count = 0
        for text in answers:
            a_count += 1
            a_id = question_id+'_a'+str(a_count)
            answer = etree.SubElement(q_node, 'ANSWER', {'id':a_id, 'position':str(a_count)})
            self.addDates(answer)
            etree.SubElement(answer, 'TEXT').text = self.process_latex(text)

        gradable = etree.SubElement(q_node, 'GRADABLE')
        etree.SubElement(gradable, 'FEEDBACK_WHEN_CORRECT').text = self.process_latex(positive_feedback)
        etree.SubElement(gradable, 'FEEDBACK_WHEN_INCORRECT').text = self.process_latex(negative_feedback)
        etree.SubElement(gradable, 'CORRECTANSWER', {'answer_id':question_id+'_a'+str(correct)})
