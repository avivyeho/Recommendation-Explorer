*This presumes that your code was tested remotely and is now on the main branch*

**1 - SSH into the server** 

Using the following command you should land in your own sub folder.  
`ssh [username]@35.189.225.155`  

**2 - You will need to navigate to the place where the github repo is on the server.**

```
/home
|-- app
|   |-- PPDB-Template-App
|   |-- recommendation-explorer (*)
|-- aviv (#)
|-- joshua (#)
|-- sanmut (#)
|--tobiaswilfert (#)
```

Depending on who reads this you will land at one of the marked spots (#)  
The github repo is at (*), so you will need to navigate there using the following command.  
`cd ../app/recommendation-explorer/`

You should now be in the root of the repo, using the following command `ls` you should see
the following (by the time reading some items may have been added)  
`App    Project    README.md`

**3 - Update the github repo**

You now need to update the github repo so that the code you added is also on the server.
You can do so by using the following command `sudo git pull`  
*This will ask for your github username and password as you are trying to pull from a private repo*

**3.1 - Install any new dependencies you use**

If your code is using depenencies that are not previoulsy used, 
the chances are high that you need to install them on ther server.
(Same way you installed them localy. If you didn't use pip3 to install them localy contact @JoshuaMoelans or @tobias-wilfert)

**4 - Restart the webapp**

All that is left is to restart the webapp. You can do so with the following command.  
`sudo systemctl restart webapp`

**5 - Logout**

You can log out of the ssh connection using the following command.  
`exit`
