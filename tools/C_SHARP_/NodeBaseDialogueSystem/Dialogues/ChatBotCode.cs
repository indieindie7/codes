using Subtegral.DialogueSystem.DataContainers;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;
namespace dialoguesBehaviour
{
    public class ChatBotCode : MonoBehaviour
    {
        [TextArea(2,3)]
        public string description;
        public DialogueContainer thisContainer;
        private void Start()
        {
            //availableChoices = new List<string>();
        }
        //public List<string> availableChoices;
    }
}
