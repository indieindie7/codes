using System;
using System.Collections.Generic;
using UnityEngine;

namespace Subtegral.DialogueSystem.DataContainers
{
    [Serializable]
    public class DialogueNodeData
    {
        public string NodeGUID;
        public string DialogueText;
        public string[] outputTags,inputTags;
        public Vector2 Position;
        public DialogueChoiceData[] choices;
    }
    public class DialogueChoiceData
    {
        public string tag, lines, targetGUID;
    }
}