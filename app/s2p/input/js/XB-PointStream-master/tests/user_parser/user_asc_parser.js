/*
  Copyright (c) 2010  Seneca College
  MIT LICENSE

  Version:  0.1
  Author:   Andor Salga
            asalga.wordpress.com
  Date:     November 16, 2010
  
  Notes:
  This parser parses .ASC filetypes. These files are ASCII
  files which have their data stored in one of the following ways:

  X, Y, Z
  X, Y, Z, R, G, B
  X, Y, Z, I, J, K
  X, Y, Z, R, G, B, I, J, K
*/

var User_ASC_Parser = (function() {

  /**
    Constructor
  */
  function User_ASC_Parser(config) {
    
    var undef;
    
    // defined once to reduce number of empty functions
    var __empty_func = function(){};
  
    var start = config.start || __empty_func;
    var parse = config.parse || __empty_func;
    var end = config.end || __empty_func;
    
    var version = "0.1";
    
    const XHR_DONE = 4;
    const STARTED = 1;
    
    // The .ASC file can contain different types of data    
    const UNKNOWN = -1;
    const VERTS = 0;
    const VERTS_COLS = 1;
    const VERTS_NORMS = 2;
    const VERTS_COLS_NORMS = 3;

    var layoutCode = UNKNOWN;
    
    var pathToFile = null;
    var fileSizeInBytes = 0;
    
    //
    var numParsedPoints = 0;
    var numTotalPoints = 0;
    var progress = 0;
    
    //
    var numValuesPerLine = -1;
    var colorsPresent = false;
    
    // keep track if onprogress event handler was called to 
    // handle Chrome/WebKit vs. Minefield differences.
    //
    // Minefield will call onprogress zero or many times
    // Chrome/WebKit will call onprogress one or many times
    var onProgressCalled = false;
    var AJAX = null;
    
    // WebGL compatibility wrapper
    try{
      Float32Array;
    }catch(ex){
      Float32Array = WebGLFloatArray;
    }
    
    /**
      @private
      
      ASC files can either contain
      X, Y, Z
      X, Y, Z, R, G, B
      X, Y, Z, I, J, K
      X, Y, Z, R, G, B, I, J, K
      
      @returns {Number}
      0 first case
      1 second case
      2 third case
      3 fourth case
    */
    var getDataLayout = function(values){
      var colorsPresent = false;
      
      // The first thing we can do is find out how many components there are.
      // If there are 9, we know we are dealing with:
      // x y z   r g b   i j k
      
      // The first line will determine how many components we have
      var firstLine = values.substr(0, values.indexOf("\n"));

      // trim leading trailing spaces
      firstLine = firstLine.replace(/^\s+/,"");
      firstLine = firstLine.replace(/\s+$/,"");

      // There may be many spaces and tabs between components, easiest way
      // is to just use split and count how many components we have
      var numWhiteSpaceChunks = firstLine.split(/\s+/).length - 1;
      
      // Vertices, Colors, Normals:
      // 1.916 -2.421 -4.0   64 32 16   -0.3727 -0.2476 -0.8942
      if(numWhiteSpaceChunks === 8){
        return VERTS_COLS_NORMS;
      }
      
      // Just vertices:
      // 1.916 -2.421 -4.0339
      if(numWhiteSpaceChunks == 2){
        return VERTS;
      }
      
      // If there are 6 components, we could have 
      // vertices and colors or 
      // vertices and normals
      
      var str = "";
      
      // We're going to try the first 500 characters and hopefully
      // figure out what we're dealing with by then.
      for(var i = 0; i < 500; i++){
        str += values[i];
      }
      
      var str_split = str.split(/\s+/);
      var data = [];
      
      for(var i = 3; i < str_split.length;){
        data.push(str_split[i++]);
        data.push(str_split[i++]);
        data.push(str_split[i++]);
        i += 3;
      }
      
      //
      for(var i = 0; i < data.length; i++){
        // if we have a component which is less than 0 or greater than 1, 
        // it must represent a part of a normal vector
        if(data[i] < 0){
          // 1.916 -2.421 -4.0   -0.3727 -0.2476 -0.8942
          return VERTS_NORMS;
        }
      }
      
      // vertices and colors:
      // -0.57831 -3.08477 -7.04268    64 32 16
      return VERTS_COLS;
    };
    
    /*
      Returns the version of this parser.
      
      @returns {String} parser version.
    */
    this.__defineGetter__("version", function(){
      return version;
    });
    
    /*
      Get the number of parsed points so far.
      
      @returns {Number} number of points parsed.
    */
    this.__defineGetter__("numParsedPoints", function(){
      return numParsedPoints;
    });
    
    /*
      Get the total number of points in the point cloud.
      
      @returns {Number}
    */
    this.__defineGetter__("numTotalPoints", function(){
      return numTotalPoints;
    });
    
    /**
      Returns the progress of downloading the point cloud between zero and one.
      
      @returns {Number} value from zero to one or -1 if unknown.
    */
    this.__defineGetter__("progress", function(){
      return progress;
    });
    
    /**
      Returns the file size of the resource in bytes.
      
      @returns {Number} size of resource in bytes.
    */
    this.__defineGetter__("fileSize", function(){
      return fileSizeInBytes;
    });
    
    /**
      @param path Path to the resource
    */
    this.load = function(path){
      pathToFile = path;

      AJAX = new XMLHttpRequest();
      
      // put a reference to the parser in the AJAX object
      // so we can give the library a reference to the
      // parser within the AJAX event handler scope.
      AJAX.parser = this;

      /**
        occurs exactly once when the resource begins
        to be downloaded
      */
      AJAX.onloadstart = function(evt){
        start(AJAX.parser);
      };
            
      /*
        occurs exactly once, when the file is done 
        being downloaded
      */
      AJAX.onload = function(evt){
      
        var ascData = AJAX.responseText;
        var chunk = null;

        // if the onprogress event didn't get called--we simply got
        // the file in one go, we can parse from start to finish.
        if(onProgressCalled === false){
          chunk = ascData;
        }
        // otherwise the onprogress event was called at least once,
        // that means we need to get the data from a specific point to the end.
        else if(ascData.length - AJAX.lastNewLineIndex > 1){
          chunk = ascData.substring(AJAX.lastNewLineIndex, ascData.length);
        }

        // if the last chunk doesn't have any digits (just spaces)
        // don't parse it.
        if(chunk && chunk.match(/[0-9]/)){
          AJAX.parseChunk(chunk);
        }

        numTotalPoints = numParsedPoints;
        
        // Indicate parsing is done. ranges from 0 to 1
        progress = 1;
        
        end(AJAX.parser);
      }
      
      /**
      */
      AJAX.parseChunk = function(chunkData){
        var chunk = chunkData;
        
        // this occurs over network connections, but not locally.
        if(chunk !== ""){
          
          if(layoutCode === UNKNOWN){
            layoutCode = getDataLayout(chunk);
            numValuesPerLine = -1;
            
            switch(layoutCode){
              case 0: numValuesPerLine = 3;
                      break;
              case 1: numValuesPerLine = 6;
                      colorsPresent = true;
                      break;
                      
              // normals present
              case 2: numValuesPerLine = 6;
                      break;
              case 3: numValuesPerLine = 9;
                      colorsPresent = true;
                      break;
            }
            gotLayout = true;
          }
          
          // trim trailing spaces
          chunk = chunk.replace(/\s+$/,"");
          
          // trim leading spaces
          chunk = chunk.replace(/^\s+/,"");
          
          // split on white space
          chunk = chunk.split(/\s+/);
          
          var numVerts = chunk.length/numValuesPerLine;
          numParsedPoints += numVerts;
                    
          var verts = new Float32Array(numVerts * 3);
          var cols = colorsPresent ? new Float32Array(numVerts * 3) : null;

          // xyz  rgb  normals
          for(var i = 0, j = 0, len = chunk.length; i < len; i += numValuesPerLine, j += 3){
            verts[j]   = parseFloat(chunk[i]);
            verts[j+1] = parseFloat(chunk[i+1]);
            verts[j+2] = parseFloat(chunk[i+2]);

            // XBPS spec for parsers requires colors to be normalized
            if(cols){
              cols[j]   = parseInt(chunk[i+3])/255;
              cols[j+1] = parseInt(chunk[i+4])/255;
              cols[j+2] = parseInt(chunk[i+5])/255;
            }
          }
                    
          // XB PointStream expects an object with named/value pairs
          // which contain the attribute arrays. These must match attribute
          // names found in the shader
          var attributes = {};
          if(verts){attributes["ps_Vertex"] = verts;}
          if(cols){attributes["ps_Color"] = cols;}
          
          parse(AJAX.parser, attributes);
        }
      };
    
      /**
        On Minefield, this will occur zero or many times
        On Chrome/WebKit this will occur one or many times
      */
      AJAX.onprogress = function(evt){
      
       if(evt.lengthComputable){
          fileSizeInBytes = evt.total;
          progress = evt.loaded/evt.total;
        }

        onProgressCalled = true;

        // if we have something to actually parse
        if(AJAX.responseText){
          var ascData = AJAX.responseText;

          // we likely stopped getting data somewhere in the middle of 
          // a line in the ASC file
          
          // 5.813 2.352 6.500 0 0 0 2.646 3.577 2.516\n
          // 1.079 1.296 9.360 0 0 0 4.307 1.181 5.208\n
          // 3.163 2.225 6.139 0 0 0 0.6<-- stopped here
          
          // So find the last known newline. Everything from the last
          // request to this last newline can be placed in a buffer.
          var lastNewLineIndex = ascData.lastIndexOf("\n");
          AJAX.lastNewLineIndex = lastNewLineIndex;
          
          // if the status just changed and we finished downloading the
          // file, grab everyting until the end. If there is only a bunch
          // of whitespace, make a note of that and don't bother parsing.
          if(AJAX.readyState === XHR_DONE){
            var chunk = ascData.substring(AJAX.startOfNextChunk, ascData.length);
            // If the last chunk doesn't have any digits (just spaces)
            // don't parse it.
            if(chunk.match(/[0-9]/)){
              AJAX.parseChunk(chunk);
            }
          }
          // if we still have more data to go
          else{
            // Start of the next chunk starts after the newline.
            var chunk = ascData.substring(AJAX.startOfNextChunk, lastNewLineIndex + 1);
            AJAX.startOfNextChunk = lastNewLineIndex + 1;
            AJAX.parseChunk(chunk);
          }
        }
      };// onprogress
      
      // open an asynchronous request to the path
      if(AJAX.overrideMimeType){
        AJAX.overrideMimeType("application/json");
      }
      AJAX.open("GET", path, true);
      AJAX.send(null);
    };// load
  }// ctor
  return User_ASC_Parser;
}());
