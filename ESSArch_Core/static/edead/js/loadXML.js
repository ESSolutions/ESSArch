function xmlLoader(pathXML) {
    var loader;
    if (window.XMLHttpRequest) {
        var loader = new XMLHttpRequest();
        loader.open("GET", pathXML ,false);
        loader.send(null);
        loader = loader.responseXML;
    } else if(window.ActiveXObject) {
        // OBS: se o arquivo XML tiver acento da erro no I.E
        var loader = new ActiveXObject("Msxml2.DOMDocument.3.0");
        loader.async = false;
        loader.load(pathXML);
    }
    return loader;
}

function getNavigator() {
    var nav = navigator.appName.toLowerCase();
    if (nav.indexOf('internet explorer') != -1) {
        return 'IE';
    } else if (nav.indexOf('netscape') != -1) {
        return 'FF';
    } else if (nav.indexOf('opera') != -1) {
        return 'OP';
    } else {
        return 'notDefined';
    }
}

//
// XML
//
$(function() {
	$( "#doxml" ).click(function() {
	
		var valid = validation();
		
		if(valid == false)
			return;
	     xmltext = "<?xml version='1.0' encoding='UTF-8'?>\n";
		 var root = $("#root").children(":first");
	
		 doXML(root);
		 var xml_pp = vkbeautify.xml(xmltext);
		 $("#processed_xml").val(xml_pp);
	});
});

function doXML(node) {
 
    var name = node.attr( "xmlname" );  
	var fieldattrs = node.children("input[attr='true']");
	var fieldselect = node.children("select[attr='true']");
	
	if(fieldattrs.length != 0 || fieldselect.length != 0)
	{
		xmltext+="<"+name;
		
		fieldselect.each(function(  ) {
			    var attrname = $(this).attr('attrname');
				var attrtext = $(this).val();
				
				if(attrtext != null && attrtext !="")
					xmltext+=" "+attrname+" ='"+attrtext+"' ";
			});
			
		fieldattrs.each(function(  ) {
			    var attrname = $(this).attr('attrname');
				var attrtext = $(this).val();
				
				if(attrtext != null && attrtext !="")
					xmltext+=" "+attrname+" ='"+attrtext+"' ";
			});
			
		xmltext+=">"
	} else {
	
		if(name == "ead") {
			xmltext+="<"+name+" xmlns='http://ead3.archivists.org/schema/'>";
		} else {
			xmltext+="<"+name+">";	
		}
	}
	var children = node.children();
	var tagname;
	
	children.each(function(  ) {
		   
		tagname = $(this)[0].tagName;
		
		if(tagname == "FIELDSET") 
		{
		    doXML($( this ));

		}
		
		if(tagname == "P") 
		{
		    var maininput = $(this).children("input[main='true']");
			var attrspan = $(this).children("span[attrfor]");
			var attrs = attrspan.children("input[attr='true']");
			var attrselect = attrspan.children("select[attr='true']");
			
			if(maininput.attr("xmlnameinp") != "null" && maininput.attr("xmlnameinp") != null ) 
				xmltext+="<"+maininput.attr("xmlnameinp");
			
			
			attrselect.each(function(  ) {
			    var attrname = $(this).attr('attrname');
				var attrtext = $(this).val();
				
				if(attrtext != null && attrtext !="")
					xmltext+=" "+attrname+" ='"+attrtext+"' ";
			});
			
			attrs.each(function(  ) {
			    var attrname = $(this).attr('attrname');
				var attrtext = $(this).val();
				if(attrtext != null && attrtext !="")
				 xmltext+=" "+attrname+" ='"+attrtext+"' ";
			});
			
			if(maininput.attr("xmlnameinp") != "null" && maininput.attr("xmlnameinp") != null ) {
				xmltext+=">"+maininput[0].value+"</"+maininput.attr("xmlnameinp")+">";
			} else {
				xmltext+=maininput[0].value;
			}
			
		}
	});
	
	
	xmltext+="</"+name+">\n";
	
	
}

function validation(){

	var reqbuttons = $("button[class='btn-danger btn']");
	
	if(reqbuttons.length != 0)
	{
		alert("Egy vagy több kötelező elem hiányzik");
		$('#processed_xml').val('');
		return false;
	}

	return true;
}

function completeInputs(){


	var id = getUrlParameter("id");
	var sdata = { id: id};
	
	jQuery.ajax({
		type: "GET", // HTTP method POST or GET
		url: "/api/information-packages/"+id+"/ead-editor/", //Where to make Ajax calls
		//data: sdata, //Form variables
		//dataType: "xml",
		success:function(response){
			
			//var xmlString = (new XMLSerializer()).serializeToString(response);
			parseMyXML(response.data);
		
		},
		error:function (xhr, ajaxOptions, thrownError){
			alert(thrownError);
		}
	});

	
}

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function SaveXML()
{
	
	$( "#doxml" ).click();
		
	var listXML = $('#processed_xml').val();
	var xmlFileName = $('#xmlfilename').val();
    var id = getUrlParameter("id");

    var csrftoken = getCookie('csrftoken');

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

	$.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
	
	if(xmlFileName == null || xmlFileName == "") {
		alert("XML filename is empty!");
	} else {
        	
		$.ajax({
			type: 'POST',
			url: "/api/information-packages/"+id+"/ead-editor/",
			data: {content: listXML},
			error: function() {
				alert("Unknown error. Data could not be written to the file.");
			},
			success: function() {
				//window.open("xml/"+xmlFileName+".xml");
                window.close();
			}
		});
	}
}


function parseMyXML(xml) {
	//var xmlString = (new XMLSerializer()).serializeToString(xml);
	
	var xmlDoc = jQuery.parseXML(xml);

	
	
	try {
		traverseXmlDoc($(xmlDoc), "", "");
		//[xmlname='theroot']:eq(0)
		for(var i = 0; i < output.length; i++)
		{
			//console.log(output[i].jqPath+" "+output[i].value);
		    //jqAddPath   jqPath  xPath   value
			if (output[i].xPath.indexOf("@") >= 0) {
			  // attributes
			  if($(output[i].jqPath).length > 0) {
			  
					//console.log("betesz: "+output[i].jqPath+" "+output[i].value);
					if($(output[i].jqPath)[0].tagName =="INPUT")
							$(output[i].jqPath).val(output[i].value);
							
					if($(output[i].jqPath)[0].tagName =="SELECT") 
						$(output[i].jqPath).val(output[i].value).attr("selected", "selected");			
			  } else {
				    console.log("missing: "+output[i].jqPath+" "+output[i].value);
			  }
			} else {
				
				if(output[i].value != "" && output[i].value != null) {
				    // this a leaf with value
					if($(output[i].jqPath).length > 0) {
					    
						if($(output[i].jqPath)[0].tagName =="P")
							$(output[i].jqPath).children("input[main='true']").val(output[i].value);
							
						if($(output[i].jqPath)[0].tagName =="FIELDSET") {
						   // console.log($(output[i].jqPath))
							$(output[i].jqPath).children("p").children("input[main='true']").val(output[i].value);
						}
					} else {
						// nincs ilyen input
						$(output[i].jqAddPath).click();
						//console.log(output[i].jqAddPath);
						if($(output[i].jqPath).length > 0) {
							if($(output[i].jqPath)[0].tagName =="FIELDSET") {
								$(output[i].jqPath).children("p").children("input[main='true']").val(output[i].value);
							}
							
							if($(output[i].jqPath)[0].tagName =="P")
								$(output[i].jqPath).children("input[main='true']").val(output[i].value);
						} else {
						
						}
					}
				} else {
					if($(output[i].jqPath).length == 0) {
						//console.log("click = "+output[i].jqAddPath);
						$(output[i].jqAddPath).click();
					}
				}
			}
			
		}
	} 
	catch (err) {
		alert(err.message);
	}
}

var first = true;

function traverseXmlDoc(xmlDoc, xPath, jqPath) {

	$(xmlDoc).children().each(function(index, Element) {

		var childElementCount = Element.childElementCount;
		var currentTagName = $(this).prop('tagName');
		var currentTagText = $(this).text();
		var currentXPathNoIndex = xPath + "/" + currentTagName;
		var currentIndex = (isNaN(indexMap[currentXPathNoIndex]) ? 1 : indexMap[currentXPathNoIndex] + 1);

		indexMap[currentXPathNoIndex] = currentIndex;

		var jqPathforAttr = jqPath;
		var currentXPath, currentJQPath, currentJQAddPath;
		if(first) {
			jqPathforAttr = jqPath;
			currentXPath = currentXPathNoIndex + "[" + currentIndex + "]";
			currentJQPath = jqPath + " [xmlname='" + currentTagName + "']" + ":eq(" + (currentIndex - 1) + ")";
			currentJQAddPath = jqPath + " [addxmlname='" + currentTagName + "']" + ":eq(" + 0 + ")";
			first = false;
		} else {
			jqPathforAttr = jqPath;
			currentXPath = currentXPathNoIndex + " > [" + currentIndex + "]";
			currentJQPath = jqPath + " > [xmlname='" + currentTagName + "']" + ":eq(" + (currentIndex - 1) + ")";
			currentJQAddPath = jqPath + " > [addxmlname='" + currentTagName + "']" + ":eq(" + 0 + ")";
		}

		var newRow = {};
		newRow.xPath = currentXPath;
		newRow.jqPath = currentJQPath;
		newRow.jqAddPath = currentJQAddPath;
		newRow.value = (childElementCount > 0 ? "" : currentTagText);
		output.push(newRow);

		$.each(this.attributes, function() {
			if(this.specified) {
				var newAttrRow = {};
				newAttrRow.xPath = currentXPath + "/@" + this.name;
				newAttrRow.jqPath = currentJQPath+" > [attrfor='"+currentTagName+"']:eq("+0+") > [attrname='" + this.name + "'][attrfor='"+currentTagName+"']" + ":eq(" + 0 + ")"; //(currentIndex - 1)
				
				newAttrRow.jqAddPath = currentJQAddPath;
				newAttrRow.value = this.value;
				output.push(newAttrRow);
			}
		});

		if (childElementCount > 0) {
			traverseXmlDoc($(this), currentXPath, currentJQPath);
		}
	});
}

function showOptAttr() {
	var optattr = $("input[attr='true']");
	var optselect = $("select[attr='true']");
	optattr.each(function(  ) {	
		if($(this).attr('req') == "false") {
			$(this).show();
			 $(this).prev('label').show();
		}
	});
	
	optselect.each(function(  ) {	
		if($(this).attr('req') == "false") {
			$(this).show();
			$(this).prev('label').show();
		}
	});
}

function hideOptAttr() {
	var optattr = $("input[attr='true']");
	var optselect = $("select[attr='true']");
	optattr.each(function(  ) {
		
		if($(this).attr('req') == "false") {
		   $(this).prev('label').hide();
		   $(this).hide();
		  }
	});
	
	optselect.each(function(  ) {	
		if($(this).attr('req') == "false") {
			$(this).prev('label').hide();
			$(this).hide();
		}
	});
	
}

var getUrlParameter = function getUrlParameter(sParam) {
    var sPageURL = decodeURIComponent(window.location.search.substring(1)),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : sParameterName[1];
        }
    }
};
