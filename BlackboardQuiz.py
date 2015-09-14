#!/usr/bin/env python

from lxml import etree
import lxml.html as html
import time
import zipfile
import re
import os
import matplotlib.pyplot as plt
from cStringIO import StringIO
from xml.sax.saxutils import escape, unescape

class Pool:
    def __init__(self, pool_name, package, description_text="Created by BlackboardQuiz!", preview = True):
        """Initialises a quiz
        """
        self.package = package
        self.pool_name = pool_name
        self.preview = preview
        
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
        if self.preview:
            self.package.zf.writestr(self.pool_name+'_preview.html', self.htmlfile)
        self.package.embed_resource("assessment/x-bb-pool", '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.pool, pretty_print=True))

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
        self.resource_counter = 0
        self.embedded_paths = {}
        #Create the manifest file
        self.bbNS = 'http://www.blackboard.com/content-packaging/'
        self.manifest = etree.Element("manifest", {'identifier':'man00001'}, nsmap={'bb':self.bbNS})
        organisation = etree.SubElement(self.manifest, "organization", {'default':'toc00001'})
        etree.SubElement(organisation, 'tableofcontents', {'identifier':'toc00001'})
        self.resources = etree.SubElement(self.manifest, 'resources')

        self.useLaTeX = useLaTeX
        from matplotlib import rc
        if self.useLaTeX:
            #Use latex (not mathtex) for better but slower results
            rc('text', usetex=True)
            
    def close(self):
        #Write additional data to implement the course name
        parentContext = etree.Element("parentContextInfo")
        etree.SubElement(parentContext, "parentContextId").text = self.courseID
        self.embed_resource("resource/x-mhhe-course-cx", '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(parentContext, pretty_print=True))

        #Finally, write the manifest file
        self.zf.writestr('imsmanifest.xml', '<?xml version="1.0" encoding="utf-8"?>\n'+etree.tostring(self.manifest, pretty_print=True))

        self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def createPool(self, pool_name, description_text="Created by BlackboardQuiz!"):
        return Pool(pool_name, self, description_text)

    def embed_resource(self, type, content):
        self.resource_counter += 1
        name = 'res'+format(self.resource_counter, '05')
        resource = etree.SubElement(self.resources, 'resource', {'identifier':name, 'type':type})
        resource.attrib[etree.QName(self.bbNS, 'base')] = name
        resource.attrib[etree.QName(self.bbNS, 'file')] = name+'.dat'
        
        self.zf.writestr(name+'.dat', content)

    def embed_file_data(self, name, content):
        """Embeds a file (given a name and content) to the quiz and returns the
        unique id of the file, and the path to the file in the zip
        """                

        #First, we need to process the path of the file, and embed xid
        #descriptors for each directory/subdirectory
        
        #Split the name into filename and path
        path, filename = os.path.split(name)

        #Simplify the path (remove any ./ items and simplify ../ items to come at the start)
        if (path != ""):
            path = os.path.relpath(path)
        
        #Split the path up into its components
        def rec_split(s):
            rest, tail = os.path.split(s)
            if rest in ('', os.path.sep):
                return [tail]
            return rec_split(s) + [tail]

        path = rec_split(path)
        root, ext = os.path.splitext(filename)

        def processDirectories(path, embedded_paths, i=0):
            #Keep processing until the whole path is processed
            if i >= len(path):
                return path

            #Slice any useless entries from the path
            if i==0 and (path[0] == ".." or path[0] == '/' or path[0] == ''):
                path = path[1:]
                return processDirectories(path, embedded_paths, i)

            #Check if the path is already processed
            if path[i] in embedded_paths:
                new_e_paths = embedded_paths[path[i]][1]
                path[i] = embedded_paths[path[i]][0]
            else:
                #Path not processed, add it
                descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
                relation = etree.SubElement(descriptor_node, 'relation')
                resource = etree.SubElement(relation, 'resource')

                self.next_xid += 1
                transformed_path = path[i]+'__xid-'+str(self.next_xid)+'_1'
                etree.SubElement(resource, 'identifier').text = str(self.next_xid)+'_1' + '#' + '/courses/'+self.courseID+'/' + os.path.join(*(path[:i+1]))
                embedded_paths[path[i]] = [transformed_path, {}]
                new_e_paths = embedded_paths[path[i]][1]

                path[i] = transformed_path
                
                self.zf.writestr(os.path.join('csfiles/home_dir', *(path[:i+1]))+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=True))

            return processDirectories(path, new_e_paths, i+1)

        processDirectories(path, self.embedded_paths)
        
        #Finally, assign a xid to the file itself
        self.next_xid += 1
        filename = root + '__xid-'+str(self.next_xid)+'_1' + ext

        #Merge the path pieces and filename
        path = path + [filename]
        path = os.path.join(*path)
        filepath = os.path.join('csfiles/home_dir/', path)
        self.zf.writestr(filepath, content)
        
        descriptor_node = etree.Element("lom") #attrib = {'xmlns':, 'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation':'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd'}
        relation = etree.SubElement(descriptor_node, 'relation')
        resource = etree.SubElement(relation, 'resource')
        etree.SubElement(resource, 'identifier').text = str(self.next_xid) + '#' + '/courses/'+self.courseID+'/'+path
        self.zf.writestr(filepath+'.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'+etree.tostring(descriptor_node, pretty_print=True))
        return str(self.next_xid)+'_1', filepath

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
            output_bb += ' '+key+'="'+value+'"'
            output_html += ' '+key+'="'+value+'"'
        output_bb += '>'
        output_html += '>'
        return output_bb, output_html
        
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

        return buffer_.getvalue(), bbox.size[0], bbox.size[1]

    def embed_latex(self, formula, display=False):
        """Renders a LaTeX formula to an image, embeds the image in the quiz
        and returns a img tag which can be used in the text of a
        question or answer.
        """
        name = "LaTeX/eq"+str(self.equation_counter)+".png"
        self.equation_counter += 1


        img_data, width_px, height_px = self.render_latex(formula)

        #This gives a 22px=1em height
        width_em = width_px / 22.0
        height_em = height_px / 22.0
        
        if display:
            if self.useLaTeX:
                formula = (r'\displaystyle ')+formula
            attrib = {'style':'display:block;margin-left:auto;margin-right:auto;height:'+str(height_em)+'em;width:'+str(width_em)+'em;'}
        else:
            attrib = {'style':'vertical-align:middle; height:'+str(height_em)+'em;width:'+str(width_em)+'em;'}

        attrib['alt'] = escape(formula)
        
        return self.embed_image(name, img_data, attrib=attrib)

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
                    
        in_string = in_string.split('$$')
        html_string = html_string.split('$$')
        for i in range(1, len(in_string), 2):
            bb_img, html_img = self.embed_latex(in_string[i], True)
            in_string[i] = bb_img
            html_string[i] = html_img
        in_string = ''.join(in_string)
        html_string = ''.join(html_string)

        #Process inline LaTeX equations
        in_string = in_string.split('$')
        html_string = html_string.split('$')
        for i in range(1, len(in_string), 2):
            bb_img, html_img = self.embed_latex(in_string[i], False)
            in_string[i] = bb_img
            html_string[i] = html_img

        return ''.join(in_string), ''.join(html_string)

    def addDates(self, element):
        """Helper function to add the DATES section
        """
        dates = etree.SubElement(element, 'DATES')
        etree.SubElement(dates, 'CREATED', {'value':time.strftime('%Y-%m-%d %H:%M:%SZ')})
        etree.SubElement(dates, 'UPDATED', {'value':time.strftime('%Y-%m-%d %H:%M:%SZ')})
