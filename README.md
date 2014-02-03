#ROB-Script#
Your friendly neighborhood cross-platform "automated builds shouldn't suck" glorified bash-like scripting language.


##Authors###
Developed by [Sam Pottinger](https://gleap.org) for [LabJack](http://labjack.com).


##Motivation###
LJ-ROB (LabJack's remote orchestrated build system) simplifies cross-platform builds for LabJack's trove of cross-platform multi-architecture software involving GUIs, native libraries, and other things that go bump in the night. However, while the software behind LJ-ROB is nice, writing Python programs that integrate with ROB isn't. ROB-script feels less like Python and more like BASH while enabling **"build + test this on five computers with different OS-es and architectures all at one" kung-foo.**



##Getting Started##

###Meet the .robscript file###
Robscripts (noimnally endinging in .rob) have line command per line. The first item per line is the command followed by tab (not four spaces... tabs!) separated parameters. Sorry it's weird. Made writing a ROB-Script parser in about an hour pretty easy though!


###.robscript files have awesome templating for reusability super-powers!###
All rob scripts are run as [jinja2](http://jinja.pocoo.org/docs/) templates to make them easier to re-use between machines and build environments. How do you provide values to those jinja2 templates? A JSON file of the form:

```js
{

    'parameter_with_boolean_value': true,
    'parameter_with_numerical_value': 1.23,
    'parameter_with_str_value': 'ROB rocks!'

}
```


###Run ROB-script from your favorite shell!###
```
python robscript.py [path to robscript.rob file] [path to JSON template vals]
```

Note that this does not have your script communicate with ROB central command or its repository for built stuff.  


###Run ROB-script through ROB!###
To be continued...


##Commands for ROB-scripts##
Remember! Love not war and, for ROB-script, tabs not spaces.

###Report the status of the build###  

 *  Reference: ```"	The new status message to report.```
 *  Example: ```"	Running unit tests.```

Updates the status of this worker at ROB central command. If running robscript outside of ROB, this is a debug message printed to the shell.


###Change the working directory###
 
 *  Reference: ```/	The (preferably full) path to execute commands at .```
 *  Example: ```/	/home/build```

Will run the subsequent commands for your script from the given directory until the working directory is changed again. If you do not include this, the starting working directory will be the location of rob_script.py. Note that silly windows machines need backslashes.


###Execute a command on the shell.###

 *  Reference: ```>	The raw command to execute.```
 *  Example: ```>	git pull origin master```

Executes the given command in the current working directory exactly as written (see above).


###Upload a file to ROB.###

 *  Reference: ```^	Local path to file.	Remote name of file.```
 *  Example: ```^	/home/build/release.zip	release_mac.zip```

Uploads a file to ROB's repository for built stuff. If running robscript outside of ROB, reports that an upload would have happened but does not actually upload.


###Upload a build log to ROB.###

 *  Reference:  ```%	Remote name to give log.```
 *  Example:```%	mac_log.txt```

Upload your script's log file to ROB's repository for built stuff. If running robscript outside of ROB, reports that an upload would have happened but does not actually upload. Note that the log file will be saved locally either way.



##Developing ROB-Script##
Want to change ROB-Script itself. Good thing it's unit tested and a single Python file! Just make sure you run tests:

```python robscript_tests.py```

Hey, you might need to install [pymox](https://code.google.com/p/pymox/) to run the tests but that's no bad is it?
