using levelScripts;
using Subtegral.DialogueSystem.DataContainers;
using System;
using System.Collections;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;
using static dialoguesBehaviour.ChatBotCode;

namespace dialoguesBehaviour
{
    public class ChatBotUI : MonoBehaviour
    {
        public GameObject canvas,choicePrefab;
        public TMPro.TMP_Text _Text;
        public RectTransform contentRect;
        // public Transform[] images;
        void Start()
        {
            canvas.SetActive(false);
            output = new List<string>();
        }
        //void Update()
        //{
        //    addControl();
        //}
        public void searchTree()
        {
            searchTags = GetComponent<playerBehaviour.PlayerCharacterController>().tags;
            //for (int i = 0; i < images.Length; i++)
            //{
            //    if (images[i].childCount > 0)
            //    {
            //        searchTags.Add(images[i].GetChild(0).GetComponent<Item>().name);
            //    }
            //}
            if (searchTags.Count == 0) return;
            output = new List<string>();
          //  recursiveSearch(origin, 0);
        }
        List<string> output, searchTags;
        void recursiveSearch(DialogueNodeData d, int depth)
        {
            foreach (NodeLinkData n in theChat.thisContainer.NodeLinks)
            {
                if (n.BaseNodeGUID == d.NodeGUID && n.inputTag == searchTags[depth])
                {
                    DialogueNodeData d2 = theChat.thisContainer.DialogueNodeData.Find(x => x.NodeGUID == n.TargetNodeGUID);
                    depth++;
                    //if (depth < searchTags.Count)
                   //     recursiveSearch(d2, depth);
                    choicesUpdate(d2);
                }
            }
        //    foreach (string o in d.outputTags)
          //      output.Add(o);

        }
        public void getOuput()
        {
            print(output);
        }
        ChatBotCode theChat;
        internal void sendChat(ChatBotCode chatBotCode)
        {
            theChat = chatBotCode;
            canvas.SetActive(true);
            foreach (NodeLinkData n in theChat.thisContainer.NodeLinks)
            {
                if (!theChat.thisContainer.DialogueNodeData.Exists(x => x.NodeGUID == n.BaseNodeGUID))
                {
                    current = theChat.thisContainer.DialogueNodeData.Find(x => x.NodeGUID == n.TargetNodeGUID);
                    //  origin.searchable = true;
                    choicesUpdate(current);
                     setText(current);
                    break;
                }
            }
        }
        DialogueNodeData current;
        void choicesUpdate(DialogueNodeData d)
        {
            foreach (NodeLinkData n in theChat.thisContainer.NodeLinks)
            {
                if (n.BaseNodeGUID == d.NodeGUID)
                {
                    //if (!theChat.availableChoices.Contains(n.InputCard.ToLower()))
                    //    theChat.availableChoices.Add(n.InputCard.ToLower());
                }
            }
        }

        internal void closeChat()
        {
            canvas.SetActive(false);

        }

        void setText(DialogueNodeData data)
        {
            _Text.text = data.DialogueText;
            string answers = "";
            foreach (NodeLinkData n in theChat.thisContainer.NodeLinks)
            {
                if (n.BaseNodeGUID == current.NodeGUID)
                {
                    answers+="["+n.inputTag+"]";
                    foreach (DialogueNodeData d in theChat.thisContainer.DialogueNodeData)
                        if (d.NodeGUID == n.TargetNodeGUID)
                            answers += d.DialogueText;
                    //if (!theChat.availableChoices.Contains(n.InputCard.ToLower()))
                    //    theChat.availableChoices.Add(n.InputCard.ToLower());
                }
            }
            //foreach (string word in theChat.availableChoices)
            //{
            //    Regex regex = new Regex(word.ToLower(), RegexOptions.IgnoreCase);
            //    foreach (Match m in regex.Matches(myString))
            //    {
            //        myString = myString.Replace(m.ToString(), "<u>" + m.ToString() + "</u>");
            //    }
            //}
            print(answers);
        }
        internal void exitChat(ChatBotCode chatBotCode)
        {
            theChat = null;
            canvas.SetActive(false);
        }
    }
}

