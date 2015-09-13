#!/usr/bin/env python

from lxml import etree
import lxml.html as html
import time
import zipfile
import re

import matplotlib.pyplot as plt
from cStringIO import StringIO

class Pool:
    def __init__(self, pool_name, package, description_text="Created by BlackboardQuiz!"):
        """Initialises a quiz
        """
        self.package = package
        self.pool_name = pool_name

        #Create the question datafile
        self.pool = etree.Element("POOL")
        etree.SubElement(self.pool, 'COURSEID', {'value':self.package.courseID})
        etree.SubElement(self.pool, 'TITLE', {'value':self.pool_name})
        description = etree.SubElement(self.pool, 'DESCRIPTION')
        etree.SubElement(description, 'TEXT').text = description_text
        self.package.addDates(self.pool)
        self.questionlist = etree.SubElement(self.pool, 'QUESTIONLIST')
        self.question_counter = 0

        #Create the manifest file

        self.htmlfile = "<html><head><style>li.correct, li.incorrect{list-style-type:none;} li.correct:before{content:'\\2713\\0020'}\nli.incorrect:before{content:'\\2718\\0020'}</style></head><body><p>Questions<ul>"

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.package.zf.writestr(self.pool_name+'_preview.html', self.htmlfile)
        self.package.embed_resource(self.pool_name, "assessment/x-bb-pool", '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.pool, pretty_print=True))

    def addQuestion(self, text, answers, correct, positive_feedback="Good work", negative_feedback="That's not correct"):
        self.question_counter += 1 
        question_id = 'q'+str(self.question_counter)
        #Add the question to the list of questions
        etree.SubElement(self.questionlist, 'QUESTION', {'id':question_id, 'class':'QUESTION_MULTIPLECHOICE'})
        #Add the actual question node
        q_node = etree.SubElement(self.pool, 'QUESTION_MULTIPLECHOICE', {'id':question_id})
        self.package.addDates(q_node)
        body = etree.SubElement(q_node, 'BODY')
        bb_question_text, html_question_text = self.package.process_string(text)
        self.htmlfile += '<li>'+html_question_text+'<ul>'
        etree.SubElement(body, 'TEXT').text = bb_question_text
        flags = etree.SubElement(body, 'FLAGS', {'value':'true'})
        etree.SubElement(flags, 'ISHTML', {'value':'true'})
        etree.SubElement(flags, 'ISNEWLINELITERAL')
        
        a_count = 0
        for text in answers:
            a_count += 1
            a_id = question_id+'_a'+str(a_count)
            answer = etree.SubElement(q_node, 'ANSWER', {'id':a_id, 'position':str(a_count)})
            self.package.addDates(answer)
            bb_answer_text, html_answer_text = self.package.process_string(text)
            etree.SubElement(answer, 'TEXT').text = bb_answer_text

            classname="incorrect"
            if (a_count == correct):
                classname="correct"

            self.htmlfile += '<li class="'+classname+'">'+html_answer_text+'</li>'

        gradable = etree.SubElement(q_node, 'GRADABLE')
        bb_pos_feedback_text, html_pos_feedback_text = self.package.process_string(positive_feedback)
        bb_neg_feedback_text, html_neg_feedback_text = self.package.process_string(negative_feedback)
        etree.SubElement(gradable, 'FEEDBACK_WHEN_CORRECT').text = bb_pos_feedback_text
        etree.SubElement(gradable, 'FEEDBACK_WHEN_INCORRECT').text = bb_neg_feedback_text
        etree.SubElement(gradable, 'CORRECTANSWER', {'answer_id':question_id+'_a'+str(correct)})

        self.htmlfile += '</ul>'
        self.htmlfile += '<div>+:'+html_pos_feedback_text+'</div>'
        self.htmlfile += '<div>-:'+html_neg_feedback_text+'</div>'
        self.htmlfile += '</li>'

class Package:
    def __init__(self, courseID="IMPORT", useLaTeX=False):
        """Initialises a Blackboard package
        """
        self.courseID = courseID
        self.embedded_files = {}
        try:
            import zlib
            compression = zipfile.ZIP_DEFLATED
        except:
            compression = zipfile.ZIP_STORED
        self.zf = zipfile.ZipFile(self.courseID+'.zip', mode='w', compression=compression)
        self.next_xid = 1000000
        self.equation_counter = 0
        self.resource_counter = 1

        #Create the manifest file
        self.manifest = etree.Element("manifest", {'identifier':'man00001'})
        organisation = etree.SubElement(self.manifest, "organization", {'default':'toc00001'})
        etree.SubElement(organisation, 'tableofcontents', {'identifier':'toc00001'})
        self.resources = etree.SubElement(self.manifest, 'resources')

        self.useLaTeX = useLaTeX
        if self.useLaTeX:
            #Use latex (not mathtex) for better but slower results
            from matplotlib import rc
            rc('text', usetex=True)            

    def close(self):
        self.zf.writestr('imsmanifest.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.manifest, pretty_print=True))
        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def createPool(self, pool_name, description_text="Created by BlackboardQuiz!"):
        return Pool(pool_name, self, description_text)


    def embed_resource(self, name, type, content):
        resource = etree.SubElement(self.resources, 'resource', {'baseurl':name, 'file':name+'.dat', 'identifier':name, 'type':type})
        self.zf.writestr(name+'.dat', content)

    def embed_file_data(self, name, content = None):
        """Embeds a file (given a name and content) to the quiz and returns the
        unique id of the file, and the path to the file in the zip
        """                
        self.next_xid += 1
        name = name.split('.')
        path = 'csfiles/home_dir/'+self.courseID+'/'+name[0]+'__xid-'+str(self.next_xid)+'_1.'+name[1]
        self.zf.writestr(path, content)
        return str(self.next_xid)+'_1', path

    def render_latex(self, formula, fontsize=12, dpi=150, format_='png'):
        """Renders LaTeX expression to bitmap image data.
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
        plt.close(fig)

        #This gives a 22px em height
        return buffer_.getvalue()

    def embed_file(self, filename, file_data=None, attrib={}):
        """Embeds a file, and returns an img tag for use in blackboard, and an equivalent for html.
        """
        #Check if it is a real file being embedded
        if file_data == None:
            #Check if this file has already been embedded
            if filename in self.embedded_files:
                #It has, return the already embedded data
                return self.embedded_files[filename]

            #It has not, load the data
            with open(filename, mode='rb') as file:
                file_data = file.read()
            xid, path = self.embed_file_data(filename, file_data)
            self.embedded_files[filename] = (xid, path)
            return xid, path
        else:
            return self.embed_file_data(filename, file_data)

    def embed_image(self, filename, img_data=None, attrib={}):
        xid, path = self.embed_file(filename, img_data)
        output_bb = '<img src="@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-'+xid+'"'
        output_html = '<img src="'+path+'"'
        for key, value in attrib.items():
            output_bb += " "+key+'="'+value+'"'
            output_html += " "+key+'="'+value+'"'
        output_bb += '>'
        output_html += '>'
        return output_bb, output_html
        
    def embed_latex(self, formula, attrib={}):
        """Renders a LaTeX formula to an image, embeds the image in the quiz
        and returns a img tag which can be used in the text of a
        question or answer.
        """
        name = "eq"+str(self.equation_counter)+".png"
        self.equation_counter += 1
        return self.embed_image(name, self.render_latex(formula), attrib=attrib)

    def process_string(self, in_string):
        """Scan a string for LaTeX equations, image tags, etc, and process them.
        """
        #Process img tags
        pattern = re.compile(r"<img.*?>")

        def img_src_processor(img_txt, html_mode):
            img_tag = html.fragment_fromstring(img_txt)
            xid, path = self.embed_file(img_tag.attrib['src'])
            if html_mode:
                img_tag.attrib['src'] = path
            else:
                img_tag.attrib['src'] = '@X@EmbeddedFile.requestUrlStub@X@bbcswebdav/xid-'+xid
            return html.tostring(img_tag)

        html_string = pattern.sub(lambda match : img_src_processor(match.group(0), True), in_string)
        in_string = pattern.sub(lambda match : img_src_processor(match.group(0), False), in_string)
        
        #Process display LaTeX equations
        in_string = in_string.split('$$')
        html_string = html_string.split('$$')
        for i in range(1, len(in_string), 2):
            if self.useLaTeX:
                in_string[i] = (r'\displaystyle ')+in_string[i]
            bb_img, html_img = self.embed_latex(in_string[i], attrib={'style':'display:block;margin-left:auto;margin-right:auto;'})
            in_string[i] = bb_img
            html_string[i] = html_img
        in_string = ''.join(in_string)
        html_string = ''.join(html_string)

        #Process inline LaTeX equations
        in_string = in_string.split('$')
        html_string = html_string.split('$')
        for i in range(1, len(in_string), 2):
            bb_img, html_img = self.embed_latex(in_string[i], attrib={'style':'vertical-align:bottom; height:1.1em;'})
            in_string[i] = bb_img
            html_string[i] = html_img

        return ''.join(in_string), ''.join(html_string)

    def addDates(self, element):
        """Helper function to add the DATES section
        """
        dates = etree.SubElement(element, 'DATES')
        etree.SubElement(dates, 'CREATED', {'value':time.strftime('%Y-%m-%d %H:%M:%SZ')})
        etree.SubElement(dates, 'UPDATED', {'value':time.strftime('%Y-%m-%d %H:%M:%SZ')})
