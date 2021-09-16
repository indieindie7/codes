using Subtegral.DialogueSystem.DataContainers;
using System;
using System.Collections;
using System.Collections.Generic;
using UnityEditor.Experimental.GraphView;
using UnityEngine;
using UnityEngine.UIElements;

namespace Subtegral.DialogueSystem.Editor
{
    public class DialogueNode : Node
    {
        public string DialogueText, GUID;
        public List<TextField> outputCards;
        public bool EntyPoint = false;
        public List<Port> outputPorts, inputPorts;
        public List<DialogueChoiceData> choiceDatas;
    }
}