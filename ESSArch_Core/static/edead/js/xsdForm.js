// globals

var ownxml;
var complexTypes;
var groups;
var attrgroups;
var elemRoot;
var indexMap = {};
var output = [];
//var ignoredTypes = ["m.mixed.basic", "m.mixed.basic.plus.elements", "m.access", "m.mixed.basic.plus.access"];
var ignoredTypes = ["m.mixed.basic", "m.mixed.basic.plus.elements", "m.mixed.basic.plus.access"];
var objectNames = [];
var loadXML = false;
var addText = "Add ";

var prefix = "xs:";



function objectName(xmlName) {
    this.xmlName = xmlName;
   this.keys = new Array();
    this.data = new Object();

    this.put = function (key, value) {
        if (this.data[key] == null) {
            this.keys.push(key);
        }
        this.data[key] = value;
    };

    this.get = function (key) {
        return this.data[key];
    };


    this.isEmpty = function () {
        return this.keys.length == 0;
    };

    this.size = function () {
        return this.keys.length;
    };
}

function generateForm(xsdFile,containerId, force) {
    try {
	
	   if(force)
	    ownxml = null;
	
		if(getBrowser() == 'Chrome')
			prefix = "";
	   
	   if(ownxml == null)
	   {
			ownxml = xmlLoader(xsdFile);
			
			complexTypes = ownxml.getElementsByTagName(prefix+"complexType");
			groups = ownxml.getElementsByTagName(prefix+"group");
			//attrgroups = ownxml.getElementsByTagName("xs:attributeGroup");
			var tagroot  = ownxml.getElementsByTagNameNS('http://www.w3.org/2001/XMLSchema','schema')[0];
			elemRoot = getNodeByTagName(tagroot, 'xs:element');
		}

		var level = 0;
		$("#root").empty();
        var elHtml = parseElement(elemRoot, level, $("#root"), null, null, null);
	
       //completeInputs();
	   

    } catch (myError) {
        alert( myError.name + ': ' + myError.message + "\n" + myError);
    }
}

function  parseElement(xmlNode, level, parentHtml, minOccurs, maxOccurs, but) {

    if(minOccurs == "0") {
		createButton(xmlNode, level, parentHtml, minOccurs, maxOccurs, null, false);
	} else {
	
		var ctype;
		var type = getValueAttributeByName(xmlNode, "type");
		var value = getValueAttributeByName(xmlNode, "fixed");
		var ElementName = getValueAttributeByName(xmlNode, "name");
		minOccurs = getValueAttributeByName(xmlNode, "minOccurs");
		maxOccurs = getValueAttributeByName(xmlNode, "maxOccurs");
		
		if(minOccurs != "0") { 
		
			if(type == "xs:string") {
				createInputField(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, false, ElementName, value);
			} else { 
		
				for (var i = 0; i < complexTypes.length; i++) {
					ctype = getValueAttributeByName(complexTypes[i], "name");
					
					if(ctype == type)
					{
						parseComplexType(complexTypes[i], level, parentHtml, minOccurs, maxOccurs, but, false, ElementName, value);
					}
					
				}
			}
			
		} else {
		   createButton(xmlNode, level, parentHtml, minOccurs, maxOccurs, null, false);
		}
	}
}

function  parseComplexType(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, fromExtension, ElementName, value) {

    var name = getValueAttributeByName(xmlNode, "name");
	
	if($.inArray(name, ignoredTypes) > -1)
		return;
		
	var mixed = getValueAttributeByName(xmlNode, "mixed");
	
    var isFieldset = false;
	var children = xmlNode.childNodes;
	for(var i = 0; i < children.length; i++)
	{
		if(children[i].tagName == "xs:simpleContent" || children[i].tagName == "xs:complexContent" || children[i].tagName == "xs:group" ||
		children[i].tagName == "xs:choice" || children[i].tagName == "xs:sequence" )
			isFieldset = true;
	}
	
	if(isFieldset) {
	    actfield = parentHtml;
		
		if(fromExtension == false) {
			actfield = createFieldset(xmlNode, level, minOccurs, maxOccurs, but, name, parentHtml, ElementName);
			
			if(but != null)
			    but = null;
		} else {
			createAttributes(xmlNode, parentHtml);
			parseAttributeGroup(xmlNode, parentHtml);
		}
		
			
	    for(var i = 0; i < children.length; i++)
	    {
			if(children[i].tagName == "xs:sequence") {
			     minOccurs = getValueAttributeByName(children[i], "minOccurs");
				maxOccurs = getValueAttributeByName(children[i], "maxOccurs");
				parseSequence(children[i], level, actfield, minOccurs, maxOccurs, but);
			}
			
			if(children[i].tagName == "xs:group") {
			    minOccurs = getValueAttributeByName(children[i], "minOccurs");
				maxOccurs = getValueAttributeByName(children[i], "maxOccurs");
				parseGroup(children[i], level, actfield, minOccurs, maxOccurs, but);
			}
			
			if(children[i].tagName == "xs:choice") {
			    minOccurs = getValueAttributeByName(children[i], "minOccurs");
				maxOccurs = getValueAttributeByName(children[i], "maxOccurs");
				parseChoice(children[i], level, actfield, minOccurs, maxOccurs, but);
			}
			
			if(children[i].tagName == "xs:complexContent") {
				parseComplexContent(children[i], level, actfield, minOccurs, maxOccurs, but, name);
			}
			
			if(children[i].tagName == "xs:simpleContent") {
			    console.log("simpleContent in ComplexType");
				//parseSequence(children[i], level, actfield, minOccurs, maxOccurs, but);
			}
			
			
		}
	   
	} else {
	  
	   if(minOccurs == null || minOccurs=="null") {     
		  createInputField(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, false, ElementName, value);
		} else {
		
		    if(but != null) {
				createInputField(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, false, ElementName, value);
			} else {
				createButton(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, false);
			}
		}
		
	}
	
   
}	

function parseSequence(xmlNode, level, parentHtml, minOccurs, maxOccurs, but) {

    minOccurs = getValueAttributeByName(xmlNode, "minOccurs");
	maxOccurs = getValueAttributeByName(xmlNode, "maxOccurs");

	var children = xmlNode.childNodes;
	for(var i = 0; i < children.length; i++)
	{
		if(children[i].tagName == "xs:element") {
			parseElement(children[i], level, parentHtml, minOccurs, maxOccurs, but);
		}
		
		if(children[i].tagName == "xs:group") {
			parseGroup(children[i], level, parentHtml, minOccurs, maxOccurs, but);
		}
		
		if(children[i].tagName == "xs:choice") {
			parseChoice(children[i], level, parentHtml, minOccurs, maxOccurs, but);
		}
		
		if(children[i].tagName == "xs:sequence") {
			parseSequence(children[i], level, parentHtml, minOccurs, maxOccurs, but);
		}
	}
	
}

function parseGroup(xmlNode, level, parentHtml, minOccurs, maxOccurs, but) {
    var gtype = getValueAttributeByName(xmlNode, "ref");
	//minOccurs = getValueAttributeByName(xmlNode, "minOccurs");
	//console.log(gtype);
	//if(gtype == "m.access")
	//	console.log("m.access");
	
	if($.inArray(gtype, ignoredTypes) > -1)
		return;
	
	if(minOccurs == null || minOccurs == "null")
		minOccurs = getValueAttributeByName(xmlNode, "minOccurs");
	
	if(maxOccurs == null || maxOccurs == "null")
		maxOccurs = getValueAttributeByName(xmlNode, "maxOccurs");
	
    
	for (var i = 0; i < groups.length; i++) {
		ctype = getValueAttributeByName(groups[i], "name");
		
		if(ctype == gtype)
		{
			//console.log(ctype);
			var children = groups[i].childNodes;
			for(var j = 0; j < children.length; j++)
			{
				if(children[j].nodeType == 1) {
					if(children[j].tagName == "xs:choice") {
						
						parseChoice(children[j], level, parentHtml, minOccurs, maxOccurs, but);
					}
					
					if(children[j].tagName == "xs:sequence") {
						parseSequence(children[j], level, parentHtml, minOccurs, maxOccurs, but);
					}
				}
			}
		}

	}
}

function parseChoice(xmlNode, level, parentHtml, minOccurs, maxOccurs, but) {
	
	var childrenChoice = xmlNode.childNodes;
	
	//console.dir(xmlNode);
	
	var choiceminOccurs = getValueAttributeByName(xmlNode, "minOccurs");
	var choicemaxOccurs = getValueAttributeByName(xmlNode, "maxOccurs");
	
	if(choiceminOccurs != null)
		minOccurs = choiceminOccurs;
		
	if(choicemaxOccurs != null)
		maxOccurs = choicemaxOccurs;
	
	
	for(var j = 0; j < childrenChoice.length; j++)
	{
	    if(childrenChoice[j].nodeType == 1) {
			
			if(childrenChoice[j].tagName == "xs:element") {
				createButton(childrenChoice[j], level, parentHtml, minOccurs, maxOccurs, but, true);
			}
			
			if(childrenChoice[j].tagName == "xs:sequence") {
				parseSequence(childrenChoice[j], level, parentHtml, minOccurs, maxOccurs, but);
			}
			
			if(childrenChoice[j].tagName == "xs:group") {
				parseGroup(childrenChoice[j], level, parentHtml, minOccurs, maxOccurs, but);
			}
			
			if(childrenChoice[j].tagName == "xs:choice") {
				parseChoice(childrenChoice[j], level, parentHtml, minOccurs, maxOccurs, but);
			}
		}
	}

}

function parseComplexContent(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, parentName) {
	
	var children = xmlNode.childNodes;
	
	for(var j = 0; j < children.length; j++)
	{
		if(children[j].nodeType == 1) {
			if(children[j].tagName == "xs:restriction") {
				parseRestriction(children[j], level, parentHtml, minOccurs, maxOccurs, but);
				//console.log("restriction in ComplexContent");
			}
			
			if(children[j].tagName == "xs:extension") {
				parseExtension(children[j], level, parentHtml, minOccurs, maxOccurs, but);
			}
		}
	}
}

function parseRestriction(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, parentName) {
	var base = getValueAttributeByName(xmlNode, "base");
	var ctype;
	
	for (var i = 0; i < complexTypes.length; i++) {
		ctype = getValueAttributeByName(complexTypes[i], "name");
		
		if(ctype == base)
		{
			parseComplexType(complexTypes[i], level, parentHtml, minOccurs, maxOccurs, but, true, null, null);
		}
		
	}
	
	var attrs = xmlNode.getElementsByTagName(prefix+"attribute");
	var name, isfixed;

	for (var j = 0; j < attrs.length; j++) {
		
		isfixed = getValueAttributeByName(attrs[j], "fixed");
		
		if(isfixed != null)
		{
			name = getValueAttributeByName(attrs[j], "name");
			var attrinput =parentHtml.children("input[attrname='"+name+"']");
			
			attrinput.val(isfixed);
		    attrinput.attr('disabled','disabled');
		}
	}
	
	//createAttributes(xmlNode, parentHtml);
	//parentHtml.append("<p>Szevasz Tavasz!</p>")
			
}

function parseExtension(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, parentName) {

	var children = xmlNode.childNodes;
	
	for(var j = 0; j < children.length; j++)
	{
		if(children[j].nodeType == 1) {
			if(children[j].tagName == "xs:group") {
				 minOccurs = getValueAttributeByName(children[j], "minOccurs");
				maxOccurs = getValueAttributeByName(children[j], "maxOccurs");
				parseGroup(children[j], level, parentHtml, minOccurs, maxOccurs, but);
			}
			
			if(children[j].tagName == "xs:sequence") {
			   
				parseSequence(children[j], level, parentHtml, minOccurs, maxOccurs, but);
			}
		}
	}
	
	var base = getValueAttributeByName(xmlNode, "base");
	
	//if($.inArray(base, ignoredTypes) > -1)
	//	return;
	var ctype;
	
	for (var i = 0; i < complexTypes.length; i++) {
		ctype = getValueAttributeByName(complexTypes[i], "name");
		
		if(ctype == base)
		{
		    var mixed = getValueAttributeByName(complexTypes[i], "mixed"); 
			//console.log(mixed);
			if(mixed == "true" || minOccurs == null) {
				createInputField(xmlNode, level, parentHtml, minOccurs, maxOccurs, null, true, null, null);
			}
			
			parseComplexType(complexTypes[i], level, parentHtml, minOccurs, maxOccurs, but, true, null, null);
		}	
	}
	
	
	
}

function createButton(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, choice) {
    var name = getValueAttributeByName(xmlNode, "name");
	 var labelt = getLabel(xmlNode, $( "#langselect" ).val());
		
	if(labelt == null) {
		labelt = getLabelFromComplex(xmlNode, $( "#langselect" ).val());
		
		if(labelt == null)
			labelt = name;
	}
		    
			
	var buttonAdd = $('<button>');
	buttonAdd.attr('addxmlname', name);
	if(maxOccurs == "unbounded") {
		buttonAdd.attr('class', "btn-info btn");
	} else {
		buttonAdd.attr('class', "btn-success btn");
	}
	buttonAdd.attr('minOccurs', minOccurs);
	buttonAdd.attr('maxOccurs', maxOccurs);
	buttonAdd.click(function(){
		createHtmltag(buttonAdd);
	});
	buttonAdd.text(addText+labelt);
	
	if(choice) {
	    
		if(minOccurs != "0") {
			buttonAdd.attr('class', "btn-danger btn");
		} 
		buttonAdd.attr('choice', "true");
	}
	
	parentHtml.append(buttonAdd);
			
}

function createHtmltag(but) {
	var name = but.attr("addxmlname");
	var minOccurs = but.attr("minOccurs");
	var maxOccurs = but.attr("maxOccurs");
	var choice = but.attr("choice");
	
	var ctype;
	for (var i = 0; i < complexTypes.length; i++) {
		ctype = getValueAttributeByName(complexTypes[i], "name");
		
		if(ctype == name)
		{
			parseComplexType(complexTypes[i], 0, but.parent(), minOccurs, maxOccurs, but, false, null, null);
		}
		
	}
	
	if(choice != null) {
	
		var buttonParent = but.parent();
		var choiceButtons = buttonParent.children( "button[choice='true']" );
		
		choiceButtons.each(function(  ) {
			if($( this ).attr("maxOccurs") == "unbounded") {
			  $( this ).attr( 'class', "btn-info btn" ); 

			} else {
			   $( this ).attr('class', "btn-success btn"); 
			}
		});
		
		
	}
	
	if(maxOccurs == "null" || maxOccurs == null)
	  but.attr("disabled", true);

}

function deleteElement(img) {
    var parentName = img.parent()[0].tagName;
	
	if(parentName =="P") {
	    
		var parent = img.parent();
		parent.prev().removeAttr("disabled");
		
		var pparent = parent.parent();
		parent.remove();
		if(img.attr('choice') != null) {
		    
		    var choiseelemnts = 0;
			
			var children = pparent.children();
			
			children.each(function(  ) {
			  //console.log( $( this ).prop("tagName"));
				if($( this )[0].tagName == "P")
					choiseelemnts++;
					
				if($( this )[0].tagName == "FIELDSET") {
				   
					if($( this ).attr("choice") == "true")
						choiseelemnts++;
				}
					
			});
			
			if(choiseelemnts == 0) {
				var choiceButtons = pparent.children( "button[choice='true']" );
		
				choiceButtons.each(function(  ) {
				    if($( this ).attr("minOccurs") != "0")
						$( this ).attr( 'class', "btn-danger btn" ); 
				});
			}
			
		}
		
		
		
	}

	if(parentName =="LEGEND") {
	    
		var addxmlname = img.attr("removexml");
		var parent = img.parent();
		var pparent = parent.parent();
		var ppparent = pparent.parent();
		ppparent.children("button[addxmlname='"+addxmlname+"']").removeAttr("disabled");
		pparent.remove();
		
		if(img.attr('choice') != null) {
			
			var choiseelemnts = 0;
			
			var children = ppparent.children();
			
			children.each(function(  ) {
				if($( this )[0].tagName == "p")
					choiseelemnts++;
					
				if($( this )[0].tagName == "FIELDSET") {
				    
					if($( this ).attr("choice") == "true")
						choiseelemnts++;
				}
					
			});
			
			if(choiseelemnts == 0) {
				var choiceButtons = ppparent.children( "button[choice='true']" );
		
				choiceButtons.each(function(  ) {
				    if($( this ).attr("minOccurs") != "0")
						$( this ).attr( 'class', "btn-danger btn" ); 
				});
			}
			
		}
		
	}
	
} 

function createInputField(xmlNode, level, parentHtml, minOccurs, maxOccurs, but, mixed, ElementName, value) {
	    var name = getValueAttributeByName(xmlNode, "name");
		var origName = name;
		
		
		if(ElementName != null)
			name = ElementName;
			
		var labelt = getLabel(xmlNode, $( "#langselect" ).val());
		var isDis = isDisabled(xmlNode);
		var isHid = isHidden(xmlNode);
		var noInp = noInputField(xmlNode);
		
		if(maxOccurs != null && but == null && mixed == false)
			createButton(xmlNode, level, parentHtml, minOccurs, maxOccurs, but);
		
		if(labelt == null)
		    labelt = name;
	
		var p = $('<p>');
		p.attr("xmlname", name);
		
		if(mixed == false){
			if(noInp == null) {
				p.append("<label origname='"+origName+"'>"+labelt+"</label>");
			} else {
				p.append("<label class='hide' origname='"+origName+"'>"+labelt+"</label>");
			}
		}

		var input = $('<input>');
		input.attr("type", "text");
		input.attr("xmlnameinp", name);
		input.attr("main", "true");
		
		if(value != null)
		{
			input.attr("value", value);
			input.attr('disabled', 'disabled');
		}
		
		if(isDis != null)
			input.attr('disabled', 'disabled');
		
		
	
		p.append(input);
		
		
		if(but != null) {
		
		    // but choice
			var deleteimg = $('<img>');
			deleteimg.attr("src", "images/remove.gif");
			deleteimg.attr("width", "18");
			deleteimg.attr("class", "deleteimg");
			deleteimg.attr("height", "18");
			deleteimg.attr("alt", "delete");
			deleteimg.attr("removexml", name);
			//deleteimg.attr('onclick', 'deleteElement(this)');
			deleteimg.click(function(){
				deleteElement(deleteimg);
			});
			
			if(but.attr("choice") != null){
				deleteimg.attr("choice", "true");
				input.attr("choice", "true");
			}
			
			p.append(deleteimg);
			
		} else {
			input.attr("class", "reqinput");
		}
		
		if(noInp != null)
			input.attr('class', 'hide');
		
	
		var hasAttr = createAttributes(xmlNode, p);
		p.attr("class", "pattr");
		
		if(isHid != null) 
			p.attr("class", "hide");
		
		if(but == null) {
			parentHtml.append(p);
		} else {
			parentHtml.append(p);
		}
		
		
		
}


function createFieldset(xmlNode, level, minOccurs, maxOccurs, but, name, parentHtml, ElementName) {

    var labelt = getLabel(xmlNode, $( "#langselect" ).val());
	var name = getValueAttributeByName(xmlNode, "name");
	var xmlname = getXMLName(xmlNode);
	
	var origName = name;
	
	if(ElementName != null)
		name = ElementName;
	
	if(but == null){
		if(maxOccurs != null)
		    createButton(xmlNode, level, parentHtml, minOccurs, maxOccurs, but);
	}

	var fieldset =  $('<fieldset>');
	
	if(xmlname != null) {
		fieldset.attr("xmlname", xmlname);
	} else {
		fieldset.attr("xmlname", name);
	}
	
	if(labelt != null) {
		var legend = $("<legend isopen='yes' origname='"+origName+"'>"+labelt+"</legend>");
		fieldset.append(legend);
		fieldset.attr("class", "bordered");
	} else {
		labelt = name;
		var legend = $("<legend isopen='yes' origname='"+origName+"'>"+labelt+"</legend>");
		fieldset.append(legend);
		//fieldset.attr("class", "noborder");
	}
	
	if(but == null) {
		parentHtml.append(fieldset);
	} else {
		//but.after(fieldset);
		parentHtml.append(fieldset);
	}
	
	
	if(but != null) {
		var deleteimg =  $('<img>');
		deleteimg.attr("src", "images/remove.gif");
		deleteimg.attr("width", "18");
		deleteimg.attr("height", "18");
		deleteimg.attr("class", "deleteimg");
		deleteimg.attr("alt", "delete");
		deleteimg.attr("removexml", name);
		//deleteimg.attr('onclick', 'deleteElement(this)');
		deleteimg.click(function(){
				deleteElement(deleteimg);
			});
		deleteimg.attr("parent", "fieldset");
		if(but.attr("choice") != null){
			deleteimg.attr("choice", "true");
			fieldset.attr("choice", "true");
		}
		
		legend.append(deleteimg);
		
	}
	//else {
	//	if(maxOccurs != null)
	//	    createButton(xmlNode, level, parentHtml, minOccurs, maxOccurs, but);
	//}
	
	createAttributes(xmlNode, fieldset);
    parseAttributeGroup(xmlNode, fieldset);
	
	
	return fieldset;
}


function parseAttributeGroup(xmlNode, htmlElement) {

    var hasreqAttr = false;
	var ctype;
	var attrgrs = xmlNode.getElementsByTagName(prefix+"attributeGroup");
	var optattr = $("#optattr").is(':checked');
	var isreq;
	
	for(var i = 0; i < attrgrs.length; i++)
	{	
		var name = getValueAttributeByName(attrgrs[i], "ref");
		
		for (var j = 0; j < attrgroups.length; j++) {
			ctype = getValueAttributeByName(attrgroups[j], "name");
			
			if(ctype == name)
			{
				var children = attrgroups[j].childNodes;
				
				 for(var k = 0; k < children.length; k++)
				 {
					 
					hasreqAttr = true;
					
					if(children[k].tagName == "xs:attribute") {
					
					    isreq = getValueAttributeByName(children[k], "use");
					   if(optattr == false && isreq == null)
						  continue;
				  
						var firstChild = children[k].firstElementChild;
						
						if(firstChild == null) {
						   
							var attrinput = $('<input>');
							var attrlabel = $('<label>'+getValueAttributeByName(children[k], "name")+" : </label>");
							attrinput.attr("placeholder", getValueAttributeByName(children[k], "type"));
							attrinput.attr("attr", "true");
							if(isreq) {
								attrinput.attr("req", "true");
								attrinput.attr("class", "reqinput");
							} else {
								attrinput.attr("req", "false");
							}
							attrinput.attr("attrname", getValueAttributeByName(children[k], "name"));
							htmlElement.append(attrlabel);
							htmlElement.append(attrinput);
						} else {
						
							if(firstChild.nodeName == "xs:simpleType") {
								if(firstChild.firstElementChild.nodeName == "xs:restriction") {
									var enums = children[k].getElementsByTagName(prefix+"enumeration");
									var select = $('<select>');
									select.attr("attrname", getValueAttributeByName(children[k], "name"));
									select.attr("id", name+"_attr");
									select.attr("attr", "true");
									
									if(isreq) {
										select.attr("req", "true");
										select.attr("class", "reqinput");
									} else {
										select.attr("req", "false");
									}
									
									for (var ii = 0; ii < enums.length; ii++) {
										var option = $('<option/>');
										option.attr({ 'value': getValueAttributeByName(enums[ii], "value") }).text(getValueAttributeByName(enums[ii], "value"));
										select.append(option);
									}
									
									var attrlabel = $('<label>'+select.attr("attrname")+" : </label>");
									htmlElement.append(attrlabel);
									htmlElement.append(select);
									
								}
							}
						
						}
					}
				   
					if(children[k].tagName == "xs:attributeGroup") {
						parseAttributeGroup(attrgroups[j], htmlElement);
					}
	
				 }
			}
		}
	}
	
	return hasreqAttr;
}


function createAttributes(xmlNode, htmlElement) {

    var name = getValueAttributeByName(xmlNode, "name");
	var hasreqAttr = false;
	var attrs = xmlNode.getElementsByTagName(prefix+"attribute");
	var optattr = true; //$("#optattr").is(':checked');
	var isreq, isfixed;
	var attrspan = $('<span>');
	attrspan.attr("attrfor", name);
	

	for (var j = 0; j < attrs.length; j++) {
			//console.log(attrs[j].parentNode.nodeName);
			if(attrs[j].parentNode.nodeName == "xs:restriction")
			    continue;
				
		   isreq = getValueAttributeByName(attrs[j], "use");
	       if(optattr == false && isreq == null)
			  continue;
		
			isfixed = getValueAttributeByName(attrs[j], "fixed");
		    //console.log(attrs[j].attributes[k]);
			hasreqAttr = true;
			
			var firstChild = attrs[j].firstElementChild;

			//console.dir(attrs[j].children[0]);
			
			if(attrs[j].children[1] == null) {
				var attrinput = $('<input>');
				
				var labelname = getValueAttributeByName(attrs[j], "name");
				var annotlabel = getLabel(attrs[j], $( "#langselect" ).val());
				
				var value = getValueAttributeByName(attrs[j], "value");
				
				if( annotlabel != null)
					labelname = annotlabel;
						
				var attrlabel = $('<label class="italic">'+labelname+'</label>');
				if(isfixed == null) {
					attrinput.attr("placeholder", getValueAttributeByName(attrs[j], "type"));
				} else {
					attrinput.val(isfixed);
					attrinput.attr('disabled','disabled');
				}
				attrinput.attr("attr", "true");
				if(isreq) {
					attrinput.attr("req", "true");
					attrinput.attr("class", "reqinput");
				} else {
					attrinput.attr("req", "false");
				}
				attrinput.attr("attrname", getValueAttributeByName(attrs[j], "name"));
				attrinput.attr("attrfor", name);
			
				//htmlElement.appendChild(document.createElement("br"));
				
				
				//htmlElement.append(attrlabel);
				//htmlElement.append(attrinput);
				attrspan.append(attrlabel);
				attrspan.append(attrinput);
			} else {
				//console.log(attrs[j].children[1].nodeName);
				if(attrs[j].children[1].nodeName == "xs:simpleType") {
					
					if(attrs[j].children[1].firstElementChild.nodeName == "xs:restriction") {
						var enums = attrs[j].getElementsByTagName(prefix+"enumeration");
						var select = $('<select>');
						select.attr("attrname", getValueAttributeByName(attrs[j], "name"));
						select.attr("attrfor", name);
						select.attr("id", name+"_attr");
						select.attr("attr", "true");
						
						if(isreq) {
							select.attr("req", "true");
							select.attr("class", "reqinput");
						} else {
							select.attr("req", "false");
						}
						
						for (var ii = 0; ii < enums.length; ii++) {
							var option = $('<option/>');
							option.attr({ 'value': getValueAttributeByName(enums[ii], "value") }).text(getValueAttributeByName(enums[ii], "value"));
							select.append(option);
						}
						
						var labelname = select.attr("attrname");
						var annotlabel = getLabel(attrs[j], $( "#langselect" ).val());
						
						if( annotlabel != null)
							labelname = annotlabel;
						
						var attrlabel = $('<label class="italic">'+labelname+" : </label>");
						//htmlElement.append(attrlabel);
						//htmlElement.append(select);
						attrspan.append(attrlabel);
						attrspan.append(select);
					}
				}
		
			}
	}
	
	if(hasreqAttr)
		htmlElement.append(attrspan);

	return hasreqAttr;
}


function getValueAttributeByName(xmlNode,attributeName) {
    var text = null;
    for (var i = 0; i < xmlNode.attributes.length; i++) {
        if ( xmlNode.attributes[i].nodeName == attributeName ) {
            text = xmlNode.attributes[i].nodeValue;
            break;
        }
    }
    return text;
}

function getNodeByTagName(xmlNode,tagName) {
    var node = null;
    for (var i = 0; i < xmlNode.childNodes.length; i++) {
        if ( xmlNode.childNodes[i].nodeType == 1 ) {
            if ( xmlNode.childNodes[i].nodeName == tagName ) {
                node = xmlNode.childNodes[i];
                break;
            }
        }
    }
    return node;
}

function isDisabled(xmlNode)
{
	var disabled = xmlNode.getElementsByTagName("disabled");
	if(disabled != null)
	{
		if(disabled.length != 0) 
			return disabled;
	}
	return null;
}

function isHidden(xmlNode)
{
	var hidd = xmlNode.getElementsByTagName("hidden");
	if(hidd != null)
	{
		if(hidd.length != 0) 
			return hidd;
	}
	return null;
}

function noInputField(xmlNode)
{
	var noinp = xmlNode.getElementsByTagName("noinputfield");
	if(noinp != null)
	{
		if(noinp.length != 0) 
			return noinp;
	}
	return null;
}

function getHTMLStyle(xmlNode) {
	
	var dxml = xmlNode.getElementsByTagName("htmlstyle"); 
	//console.log(dxml);
	if(dxml != null)
	{ 
		if(dxml.length != 0) {
			return getText(dxml[0]); 
		}
	}
	

	return null;
}

function getLabelFromComplex(xmlNode, lang) {

	var type = getValueAttributeByName(xmlNode, "type");
	var ctype;
	var docu;
	
	for (var i = 0; i < complexTypes.length; i++) {
		ctype = getValueAttributeByName(complexTypes[i], "name");
		
		if(ctype == type)
		{
			docu = complexTypes[i].getElementsByTagName(prefix+"documentation");
	
			for(var l = 0; l < docu.length; l++) {
				if(getValueAttributeByName(docu[l], 'xml:lang') == lang)
					return getText(docu[l]);
			}
		}
	}

	return null;
}

function getXMLName(xmlNode) {
	var dxml = xmlNode.getElementsByTagName("xmlname"); 
	//console.log(dxml);
	if(dxml != null)
	{ 
		if(dxml.length != 0) {
			return getText(dxml[0]); 
		}
	}
	
	return null;
}

function getLabel(xmlNode, lang) {
	
	var docu = null;
	
	for (var i = 0; i < xmlNode.childNodes.length; i++) {
		if (xmlNode.childNodes[i].nodeType == 1 && xmlNode.childNodes[i].nodeName == 'xs:annotation' ) {
			
			docu = xmlNode.childNodes[i].getElementsByTagName(prefix+"documentation");
	
			if(docu.length != 0)
			{
				var onames = new objectName(getValueAttributeByName(xmlNode, "name"));
				for(var l = 0; l < docu.length; l++) {
					onames.put(getValueAttributeByName(docu[l], 'xml:lang'), getText(docu[l]));
				}
				//console.dir(onames);
				objectNames.push(onames);
			}
		}
	}

	
	if(docu != null) {
		for(var l = 0; l < docu.length; l++) {
			if(getValueAttributeByName(docu[l], 'xml:lang') == lang)
				return getText(docu[l]);
		}
	}
	
	return null;
}

function changeLanguage() {

	var legends = $('legend');
	var labels = $('label');
	var buttons = $('button');
	var origname;
	legends.each(function(  ) {
		origname = $(this).attr('origname');
		for(var i = 0; i < objectNames.length; i++) {
			if(objectNames[i].xmlName == origname) {
				$(this).text(objectNames[i].get($( "#langselect" ).val()));
			}
		}
				
	});
	
	labels.each(function(  ) {
		origname = $(this).attr('origname');
		
		for(var i = 0; i < objectNames.length; i++) {
			if(objectNames[i].xmlName == origname) {
				$(this).text(objectNames[i].get($( "#langselect" ).val()));
			}
		}
				
	});
	
	var lang = $( "#langselect" ).val();
	for (var i = 0; i < complexTypes.length; i++) {
		ctype = getValueAttributeByName(complexTypes[i], "name");
		
		if(ctype == "addText")
		{
			docu = complexTypes[i].getElementsByTagName(prefix+"documentation");
	
			for(var l = 0; l < docu.length; l++) {
				if(getValueAttributeByName(docu[l], 'xml:lang') == lang)
					addText = getText(docu[l]);
			}
		}
	}
	
	//alert(addText);
	
	buttons.each(function(  ) {
		origname = $(this).attr('addxmlname');
		for(var i = 0; i < objectNames.length; i++) {
			if(objectNames[i].xmlName == origname) {
				$(this).text(addText+" "+objectNames[i].get($( "#langselect" ).val()));
			}
		}
	});
			
	
}

function getText(xmlNode) {
    if ( getNavigator() == 'IE' ) {
        return xmlNode.firstChild.nodeValue;
    } else {
        return xmlNode.textContent;
    }
}

function getBrowser() { 
     if((navigator.userAgent.indexOf("Opera") || navigator.userAgent.indexOf('OPR')) != -1 ) 
    {
        return 'Opera';
    }
    else if(navigator.userAgent.indexOf("Chrome") != -1 )
    {
        return 'Chrome';
    }
    else if(navigator.userAgent.indexOf("Safari") != -1)
    {
        return 'Safari';
    }
    else if(navigator.userAgent.indexOf("Firefox") != -1 ) 
    {
        return 'Firefox';
    }
    else if((navigator.userAgent.indexOf("MSIE") != -1 ) || (!!document.documentMode == true )) //IF IE > 10
    {
      return 'IE'; 
    }  
    else 
    {
       return 'unknown';
    }
}
