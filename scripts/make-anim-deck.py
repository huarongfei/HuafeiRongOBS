# -*- coding: utf-8 -*-
"""向 pptx 注入标准 PowerPoint 动画（p:timing），用于自研引擎动画开发/回归"""
import zipfile, shutil, re, os

SRC = r"D:\HuafeirongOBS\tools\test\rich-deck.pptx"
DST = r"D:\HuafeirongOBS\tools\test\anim-deck.pptx"

def anim_block(steps):
    """steps: list of (spid, presetClass, presetID, filter, transition, dur)"""
    inner = []
    for i, (spid, pclass, pid, filt, trans, dur) in enumerate(steps):
        base = 5 + i * 10
        inner.append(f'''
                <p:par>
                  <p:cTn id="{base}" fill="hold">
                    <p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="{base+1}" fill="hold">
                          <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                          <p:childTnLst>
                            <p:par>
                              <p:cTn id="{base+2}" presetID="{pid}" presetClass="{pclass}" presetSubtype="0" fill="hold" grpId="0" nodeType="clickEffect">
                                <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                                <p:childTnLst>
                                  <p:set>
                                    <p:cBhvr>
                                      <p:cTn id="{base+3}" dur="1" fill="hold">
                                        <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                                      </p:cTn>
                                      <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                                      <p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>
                                    </p:cBhvr>
                                    <p:to><p:strVal val="visible"/></p:to>
                                  </p:set>
                                  <p:animEffect transition="{trans}" filter="{filt}">
                                    <p:cBhvr>
                                      <p:cTn id="{base+4}" dur="{dur}"/>
                                      <p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>
                                    </p:cBhvr>
                                  </p:animEffect>
                                </p:childTnLst>
                              </p:cTn>
                            </p:par>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>''')
    joined = "".join(inner)
    return f'''<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>{joined}
              </p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>'''

# 第 1 页：标题 淡入(点击1)、正文 淡入(点击2)
steps1 = [(2, "entr", 10, "fade", "in", 500),
          (4, "entr", 10, "fade", "in", 700)]
# 第 3 页：圆角矩形 淡入
steps3 = [(2, "entr", 10, "fade", "in", 600)]

zin = zipfile.ZipFile(SRC, 'r')
zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == 'ppt/slides/slide1.xml':
        xml = data.decode('utf-8')
        xml = xml.replace('</p:sld>', anim_block(steps1) + '</p:sld>')
        data = xml.encode('utf-8')
    elif item.filename == 'ppt/slides/slide3.xml':
        xml = data.decode('utf-8')
        xml = xml.replace('</p:sld>', anim_block(steps3) + '</p:sld>')
        data = xml.encode('utf-8')
    zout.writestr(item, data)
zout.close(); zin.close()
print("saved:", DST, os.path.getsize(DST), "bytes")
