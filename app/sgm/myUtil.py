def download(work_dir,url, WHITELIST=[]):
   """
   Copy the contents of a file from a given URL
   to a local file in work_dir.
   If WHITELIST is set it checks the url aganist it 
   before downloading. 
   Returns: a pair (widk_dir, local_filename)
   """
   import urllib
   import os.path
   from urlparse import urlparse

   # Whitelist check
   if WHITELIST != [] and urlparse(url).netloc not in WHITELIST:
      raise cherrypy.HTTPError(400, # Bad URL
            "URL " + url + " not in white list")

   # download
   try: 
      webFile = urllib.urlopen(url)
      localFilename = os.path.join(work_dir , url.split('/')[-1]);
      localFile = open(localFilename, 'w')
      localFile.write(webFile.read())
      webFile.close()
      localFile.close()
   except IOError:
      raise cherrypy.HTTPError(400, # Bad URL
            "Bad URL file (Can't connect to: " + url + ")")

   return (work_dir, url.split('/')[-1])



def convert_axpb(im, a, b):
   """
   Convert INT image to FLOAT, and apply axpb
   only works for gray images, for color ones must use something like
   bands=im.split()
   fbd=tuple([ ImageMath.eval('float(imA)', imA=m) for m in bands ])
   return Image.merge('F',fbd)
   """
   import Image, ImageMath
   return ImageMath.eval("float(imA)*paramA + paramB", imA=im, paramA=a, paramB=b)


def image_add_note(im, textstring, color=255):
   """
   add a note on the upper left corner of the image
   """
   import ImageDraw
   draw = ImageDraw.Draw(im)
   sz = draw.textsize(textstring)
   draw.rectangle(((0,0), sz) ,fill=0) 
   draw.text((0,0), textstring, fill=color)
   del draw
   return im






def image_add_scale(im, imrange, color=255, Rwidth=128):
   """
   add a scale on the upper left corner of the image
   """
   if im.size[0] > 128:
      import ImageDraw
      draw = ImageDraw.Draw(im)
      sz = draw.textsize(str(imrange))
      draw.rectangle(((0,sz[1]), (Rwidth,2*sz[1])) ,fill=0) 
      for i in range(0,3):
         DIF=imrange[1]-imrange[0]
         draw.text(  (int(i*(Rwidth-8)/2),sz[1]) , "%.1f" % (float(i)/2*DIF + imrange[0]), fill=color)
      for i in range(0,Rwidth):
         draw.rectangle(((i,0), (i,sz[1])) ,fill=int (color*i/Rwidth) ) 
      del draw
   return im





def generate_preview_with_scale(infilename, outfilename,range=None):
   """
   generates a preview of a grayscale image with a scale
   """
   import Image 
   im=Image.open(infilename)
   if im.mode == 'F':
      if range:
         (minVal,maxVal) = range
      else:
         (minVal,maxVal) =im.getextrema()
      #safeguard
      if maxVal-minVal == 0:
         (minVal, maxVal) = (0,1)

      im = convert_axpb(im, 65535.0/(maxVal-minVal), -65535.0*minVal/(maxVal-minVal))
      im = im.convert('I')
      # 
      # save the thumbnail
      textstring = 'RANGE:['+str(minVal) +','+ str(maxVal)+']'
      #im=image_add_note(im,textstring,color=65535)
      im=image_add_scale(im,(minVal,maxVal),color=65535)
      im.save(outfilename)
   else:
      im.save(outfilename)




def compute_difference(imfile, gtfile, outfile):
   """
   computes the difference image 
   """
   import Image, ImageMath
   im=Image.open(imfile)
   gt=Image.open(gtfile)
   
   tmp = ImageMath.eval("(float(imA)-float(imB))", imA=im, imB=gt)

   tmp.save(outfile)

