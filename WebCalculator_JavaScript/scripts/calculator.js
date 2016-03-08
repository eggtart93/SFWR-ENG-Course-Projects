/*
 * Software Enginnering: Web Development
 *
 * <Topic: Design of Web Calculator>
 *
 * Author: Jin Kuan Zhou <zhoujk93@hotmail.com>
 * Date: 2016-02-22
 *
 */

var CalModeEnum = {
    STD: "STAND",
    SCI: "Sci",
    CONV: "Conv",
};

var mode = CalModeEnum.STD;
var resetFlag = false;

function isNumber(n){
    return /^\-?[0-9]+\.?[0-9]*$/.test(n);
}

function key(val){
    if (val == null || resetFlag){
        document.getElementById("expr-line").innerHTML = val;
        resetFlag = false;
    } else if (document.getElementById("expr-line").innerHTML.length < 25) {
        document.getElementById("expr-line").innerHTML += val;
    } else {
        document.getElementById("result-line").innerHTML = "Max input";
    }
}

function key_exp(){
    document.getElementById("expr-line").innerHTML += "e";
}

function key_del(){
    var element = document.getElementById("expr-line");
    if (element.innerHTML.length > 0){
        element.innerHTML = element.innerHTML.substring(0,element.innerHTML.length-1);
    }
}

function key_ac(){
    document.getElementById("expr-line").innerHTML = "";
    document.getElementById("result-line").innerHTML = "";
    if (mode == CalModeEnum.SCI){
        document.getElementById("sin-input").value = "";
        document.getElementById("cos-input").value = "";
        document.getElementById("log-input").value = "";
        document.getElementById("sqrt-input").value = "";
        document.getElementById("sin-result").innerHTML = "";
        document.getElementById("cos-result").innerHTML = "";
        document.getElementById("log-result").innerHTML = "";
        document.getElementById("sqrt-result").innerHTML = "";
        if (mode == CalModeEnum.CONV){
            document.getElementById("param-1").value = "";
            document.getElementById("param-2").value = "";
        }
    }

}

function key_eval(){
    var expr = document.getElementById("expr-line").innerHTML;

    var error = /^[\xD7\xF7e]/.test(expr) || /[^0-9]$/.test(expr);

    if (error){
        document.getElementById("result-line").innerHTML = "Syntax Error";
    }
    else {
        expr = expr.replace(/\xF7/i, '/');
        expr = expr.replace(/\xD7/i, '*');
        expr = expr.replace(/e(\d+\.?\d*)/g, "*Math.pow(10, $1)");

        var result = eval(expr);

        if (!isNumber(result)){
            document.getElementById("result-line").innerHTML = "Math error";
        } else if (result.length > 25) {
            document.getElementById("result-line").innerHTML = "Max output";

        } else {
            document.getElementById("result-line").innerHTML = result;
        }
    }
    resetFlag = true;
}

function key_sci(){
    sciMode();
    var button = document.getElementById("change-mode");
    button.value = CalModeEnum.CONV;
    button.setAttribute("onClick", "key_conv()");

}

function key_conv(){
    convMode();
    var button = document.getElementById("change-mode");
    button.value = CalModeEnum.STD;
    button.setAttribute("onClick", "key_stand()");
}

function key_stand(){
    standMode();
    var button = document.getElementById("change-mode");
    button.value = CalModeEnum.SCI;
    button.setAttribute("onClick", "key_sci()");
}

function key_sin(){
    var x = document.getElementById("sin-input").value;
    if (isNumber(x)){
        x = Math.PI * x / 180;
        document.getElementById("sin-result").innerHTML = Math.sin(x).toFixed(3);
    }
    else {
        document.getElementById("sin-result").innerHTML = "Syntax Error";
    }
}

function key_cos(){
    var x = document.getElementById("cos-input").value;
    if (isNumber(x)){
        x = Math.PI * x / 180;
        document.getElementById("cos-result").innerHTML = Math.cos(x).toFixed(3);
    }
    else {
        document.getElementById("cos-result").innerHTML = "Syntax Error";
    }
}

function key_log(){
    var x = document.getElementById("log-input").value;
    if (isNumber(x)){
        if (parseFloat(x) < 0) document.getElementById("log-result").innerHTML = "Math Error";
        else document.getElementById("log-result").innerHTML = Math.log(x).toFixed(3);
    }
    else {
        document.getElementById("log-result").innerHTML = "Syntax Error";
    }
}

function key_sqrt(){
    var x = document.getElementById("sqrt-input").value;
    if (isNumber(x)){
        if (parseFloat(x) < 0) document.getElementById("sqrt-result").innerHTML = "Math Error";
        else document.getElementById("sqrt-result").innerHTML = Math.sqrt(x).toFixed(3);
    }
    else {
        document.getElementById("sqrt-result").innerHTML = "Syntax Error";
    }
}

function standMode(){
    var cal = document.getElementById("my-cal");
    if (cal.rows.length > 4) cal.deleteRow(-1);
    for (var row=1; row < cal.rows.length; row++){
        //console.log("row = " + row + ", num of cols = " + cal.rows[row].cells.length);
        var lastCol = cal.rows[row].cells.length - 1;
        for (var col=lastCol; col > 4; col--){
            cal.rows[row].deleteCell(col);
        }
    }
    mode = CalModeEnum.STD;
}

function sciMode() {
    var cal = document.getElementById("my-cal");
    addButton(cal.rows[1].insertCell(-1), "sin", key_sin);
    addTextbox(cal.rows[1].insertCell(-1), "sin-input");
    addLabel(cal.rows[1].insertCell(-1), "", "deg = ");
    addLabel(cal.rows[1].insertCell(-1), "sin-result", "");

    addButton(cal.rows[2].insertCell(-1), "cos", key_cos);
    addTextbox(cal.rows[2].insertCell(-1), "cos-input");
    addLabel(cal.rows[2].insertCell(-1), "", "deg = ");
    addLabel(cal.rows[2].insertCell(-1), "cos-result", "");

    addButton(cal.rows[3].insertCell(-1), "log", key_log);
    addTextbox(cal.rows[3].insertCell(-1), "log-input");
    addLabel(cal.rows[3].insertCell(-1), "", " = ");
    addLabel(cal.rows[3].insertCell(-1), "log-result", "");

    addButton(cal.rows[4].insertCell(-1), "\u221a", key_sqrt);
    addTextbox(cal.rows[4].insertCell(-1), "sqrt-input");
    addLabel(cal.rows[4].insertCell(-1), "", " = ");
    addLabel(cal.rows[4].insertCell(-1), "sqrt-result", "");
    mode = CalModeEnum.SCI;
}

function addButton(parent, text, handler){
    var element = document.createElement("input");
    element.type = "button";
    element.value = text;
    element.onclick = handler;
    parent.appendChild(element);
}

function addTextbox(parent, id){
    if (typeof(id) === 'undefined') id = "";
    var element = document.createElement("input");
    element.type = "text";
    element.id = id;
    parent.appendChild(element);
}

function addLabel(parent, id, text){
    var element = document.createElement("span");
    element.id = id;
    element.innerHTML = text;
    parent.appendChild(element);
}

function select(index) {
    switch (index){
        case 0:
            document.getElementById("unit-1").innerHTML = "Km = ";
            document.getElementById("unit-2").innerHTML = "m";
            break;
        case 1:
            document.getElementById("unit-1").innerHTML = "Min = ";
            document.getElementById("unit-2").innerHTML = "Sec";
            break;
        case 2:
            document.getElementById("unit-1").innerHTML = "Kg = ";
            document.getElementById("unit-2").innerHTML = "g";
            break;
        default:
            break;
    }
    document.getElementById("param-1").value = "";
    document.getElementById("param-2").value = "";
}

function conv(textbox){
    if (!textbox.value) {
        document.getElementById("param-1").value = "";
        document.getElementById("param-2").value = "";
        return;
    }

    var factor = 1;
    switch (document.getElementById("conv_list").selectedIndex) {
        case 0:
            factor = 1000; // KM TO M
            break;
        case 1:
            factor = 60; // MIN TO SEC
            break;
        case 2:
            factor = 1000; // KG TO G
            break;
        default:
            break;
    }
    if (textbox.id == "param-1") {
        if (isNumber(textbox.value)){
            document.getElementById("param-2").value = parseFloat(textbox.value) * factor;
        } else {
            document.getElementById("param-2").value = "Syntax Error";
        }
    }
    else if (textbox.id == "param-2") {
        if (isNumber(textbox.value)){
            document.getElementById("param-1").value = parseFloat(textbox.value) / factor;
        } else {
            document.getElementById("param-1").value = "Syntax Error";
        }
    }
}

function convMode() {
    var lastRow = document.getElementById("my-cal").insertRow(-1);

    // Add select list
    var conv_list = ["Kilometers to meters, meters to kilometers",
                     "Minutes to seconds, seconds to minutes",
                     "Kilograms to grams, grams to kilograms"];
    var select = document.createElement("select");
    select.id = "conv_list";
    select.setAttribute("onchange", "select(this.selectedIndex)");

    for (var i = 0; i < conv_list.length; i++){
        var option = document.createElement("option");
        option.value = conv_list[i];
        option.text = conv_list[i];
        select.appendChild(option);
    }

    var cell = lastRow.insertCell(0);
    cell.colSpan = "5";
    cell.appendChild(select);

    // add textbox for param 1
    addTextbox(lastRow.insertCell(-1), "param-1");
    addLabel(lastRow.insertCell(-1), "unit-1", "Km = ");
    addTextbox(lastRow.insertCell(-1), "param-2");
    addLabel(lastRow.insertCell(-1), "unit-2", "m");

    var textbox = document.getElementById("param-1");
    textbox.setAttribute("onchange", "conv(this)");
    textbox.setAttribute("onkeypress", "conv(this)");
    textbox.setAttribute("onpaste", "conv(this)");
    textbox.setAttribute("oninput", "conv(this)");

    textbox = document.getElementById("param-2");
    textbox.setAttribute("onchange", "conv(this)");
    textbox.setAttribute("onkeypress", "conv(this)");
    textbox.setAttribute("onpaste", "conv(this)");
    textbox.setAttribute("oninput", "conv(this)");

    mode = CalModeEnum.CONV;
}
