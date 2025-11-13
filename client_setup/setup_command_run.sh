docker run -it `
-v ("<C:\Users\WINDOWS-USERNAME\Documents\syosil-project>" + `
    ":/home/" + $env:username + "-docker/<syosil-project>") `
-e DISPLAY=host.docker.internal:0.0 `
--name syosil-ubuntu-container `
syosil-ubuntu-container
