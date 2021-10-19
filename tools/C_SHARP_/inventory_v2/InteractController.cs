using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using playerInventory;
//using levelScripts;

namespace playerBehaviour
{
    public class InteractController : MonoBehaviour
    {
        internal bool isTalking = false;
        void Start()
        {
            playerInventory = GetComponent<PlayerInventory>();
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
            playerInventory.setVisual();
        }
        public float doubleClickTime, distInteract;
        void Update()
        {
            mouseControl();
            clickControl();
        }
        void mouseControl()
        {
            if (Input.GetKeyDown(KeyCode.Tab))
            {
                Cursor.visible = !Cursor.visible;
                Cursor.lockState = !Cursor.visible ? CursorLockMode.Locked : CursorLockMode.None;
                playerInventory.setVisual();
            }
        }
        float lastTime;
        PlayerInventory playerInventory;
        void clickControl()
        {

            if (Cursor.visible && Input.GetMouseButtonDown(0))
            {
                RaycastHit hit;
                Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
                if (Time.time - lastTime < doubleClickTime)
                {
                    if (Physics.Raycast(ray, out hit, distInteract))
                    {
                        print(hit.transform);
                        if (hit.transform.tag == "Item")
                        {
                            interactItem(hit.transform.gameObject);
                        }
                        if (hit.transform.tag == "Human")
                        {
                            interactHuman(hit.transform);
                        }
                    }
                }
                lastTime = Time.time;
            }
        }

        private void interactHuman(Transform transform)
        {
            isTalking = true;
            GetComponent<dialoguesBehaviour.ChatBotUI>().sendChat(transform.GetComponent<dialoguesBehaviour.ChatBotCode>());
        }
        public void interactItem(GameObject c)
        {
            GetComponent<PlayerInventory>().generateItem(c.GetComponent<ItemLevel>());
        }
        private void OnTriggerEnter(Collider other)
        {
        }
    }
}