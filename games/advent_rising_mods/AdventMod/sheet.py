from PIL import Image
import glob,sys
fs=sorted(glob.glob(r'H:/SteamLibrary/steamapps/common/Advent Rising/System/ShotP*.bmp'))
ims=[Image.open(f).convert('RGB') for f in fs]
w,h=ims[0].size
x0,y0,x1,y1=[float(v) for v in sys.argv[2:6]] if len(sys.argv)>5 else (0.15,0.25,0.85,0.85)
c=[im.crop((int(w*x0),int(h*y0),int(w*x1),int(h*y1))).resize((480,int(480*(y1-y0)*h/((x1-x0)*w)))) for im in ims]
ch=c[0].size[1]; n=len(c)
s=Image.new('RGB',(480*5,ch*((n+4)//5)))
for i,im in enumerate(c): s.paste(im,((i%5)*480,(i//5)*ch))
s.save(sys.argv[1]); print(n)
