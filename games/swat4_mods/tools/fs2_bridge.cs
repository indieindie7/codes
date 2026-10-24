// SwatMinds bridge: file-polled TorqueScript. Drop lines into smbridge/in.txt;
// each line is eval'd, results via SMB_out() land in smbridge/out.txt.
function SMB_out(%s)
{
   %f = new FileObject();
   if (%f.openForAppend("smbridge/out.txt"))
   {
      %f.writeLine(getSimTime() @ " " @ %s);
      %f.close();
   }
   %f.delete();
}

function SMB_poll()
{
   if (isFile("smbridge/in.txt"))
   {
      %f = new FileObject();
      if (%f.openForRead("smbridge/in.txt"))
      {
         while (!%f.isEOF())
         {
            %l = %f.readLine();
            if (%l !$= "")
               eval(%l);
         }
         %f.close();
      }
      %f.delete();
      fileDelete("smbridge/in.txt");
   }
   $SMB_sched = schedule(200, 0, SMB_poll);
}

SMB_out("bridge up");
$SMB_sched = schedule(1000, 0, SMB_poll);
