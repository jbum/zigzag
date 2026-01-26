# import geetree
from lxml import etree as ET
import re

def print_logo(canvas,pw,ph,ox,oy,justify='left',filename="krazydad_logo_new_slogan.svg"):
    svg = ET.parse('assets/krazydad_logo_new_slogan.svg')

    oy -= 28   # adjust for baseline
    if justify == 'right':
        ox -= 150
    elif justify == 'center':
        ox -= 150/2

    for gelem in svg.getroot().iterdescendants(tag='{http://www.w3.org/2000/svg}g'):
        # print("Got G")
        for pelem in gelem.iterdescendants(tag='{http://www.w3.org/2000/svg}path'):
            # print("D:" + pelem.attrib['d'])
            clist = re.split('(:?[A-Za-z])',pelem.attrib['d'])[1:]
            (x1,y1,x2,y2) = (0,0,0,0)
            (px,py) = (ox,oy)
            path = canvas.beginPath()
            while len(clist) > 1:
                (cmd,pts) = clist[0:2]
                clist = clist[2:]
                pts = re.sub('-',',-',pts)
                pts = re.sub('^,','',pts)
                # print (cmd,pts)
                if cmd.upper() in 'MCSHVL':
                    plist = [float(x) for x in pts.split(',')]
                    if cmd == 'M':
                        (px,py) = (plist[0]+ox,plist[1]+oy)
                        path.moveTo(px,ph-py)
                    elif cmd == 'm':
                        (px,py) = (plist[0]+px,plist[1]+py)
                        path.moveTo(px,ph-py)
                    elif cmd == 'L':
                        (px,py) = (plist[0]+ox,plist[1]+oy)
                        path.lineTo(px,ph-py)
                    elif cmd == 'l':
                        (px,py) = (plist[0]+px,plist[1]+py)
                        path.lineTo(px,ph-py)
                    elif cmd == 'H':
                        (px) = (plist[0]+ox)
                        path.lineTo(px,ph-py)
                    elif cmd == 'h':
                        (px) = (plist[0]+px)
                        path.lineTo(px,ph-py)
                    elif cmd == 'V':
                        (py) = (plist[0]+oy)
                        path.lineTo(px,ph-py)
                    elif cmd == 'v':
                        (py) = (plist[0]+py)
                        path.lineTo(px,ph-py)
                    elif cmd == 'C':
                        (x1,y1,x2,y2,px,py) = (plist[0]+ox,plist[1]+oy,  plist[2]+ox,plist[3]+oy,    plist[4]+ox,plist[5]+oy)
                        path.curveTo(x1,ph-y1,x2,ph-y2,px,ph-py)
                    elif cmd == 'c':
                        (x1,y1,x2,y2,px,py) = (plist[0]+px,plist[1]+py,  plist[2]+px,plist[3]+py,    plist[4]+px,plist[5]+py)
                        path.curveTo(x1,ph-y1,x2,ph-y2,px,ph-py)
                    elif cmd == 'S':
                        (x1,y1,x2,y2,px,py) = (px-(x2-px),py-(y2-py),plist[0]+ox,plist[1]+oy,plist[2]+ox,plist[3]+oy)
                        path.curveTo(x1,ph-y1,x2,ph-y2,px,ph-py)
                    elif cmd == 's':
                        (x1,y1,x2,y2,px,py) = (px-(x2-px),py-(y2-py),   plist[0]+px,plist[1]+py,   plist[2]+px,plist[3]+py)
                        path.curveTo(x1,ph-y1,x2,ph-y2,px,ph-py)
                elif cmd == 'z':
                    path.close()
            canvas.drawPath(path, stroke=0, fill=1)


# for gelem in svg.getroot():
#     if '}g' in gelem.tag:
#         for pelem in gelem:
#             if '}path' in pelem.tag:

#                 # print("D:" + elem2.attrib['d'])

