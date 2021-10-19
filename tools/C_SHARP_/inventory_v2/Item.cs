using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
namespace playerInventory
{
    public class Item : MonoBehaviour, IPointerDownHandler, IPointerEnterHandler, IPointerExitHandler
    {
        internal bool isShowing;
        internal ItemLevel origin;
        // internal ItemData myData;
        void Start()
        {
            inventoryManager = GameObject.Find("PlayerScripts").GetComponent<PlayerInventory>();
        }
        internal List<ItemSpot> mySpots;
        void Update()
        {
        }
        internal void rotate()
        {
            if (!origin.canStore || (origin.canStore && !isShowing))
                transform.RotateAround(Input.mousePosition, transform.forward, 90);
        }
        PlayerInventory inventoryManager;
        public void OnPointerDown(PointerEventData eventData)
        {
            if (isShowing) return;
            if (eventData.button == PointerEventData.InputButton.Right)
            {
                if (origin.canStore)
                {
                    Debug.Log(name);
                    inventoryManager.insantiateGUI(this);
                    return;
                }
                return;
            }
            GetComponent<Image>().raycastTarget = false;
            foreach (Transform t in transform) t.GetComponent<Image>().raycastTarget = false;
            inventoryManager.startDraggin(this);
        }

        public void OnPointerEnter(PointerEventData eventData)
        {
            if (!origin.canStore) return;
            if (isShowing)
                inventoryManager.mouseStorageEnter(this);
        }

        public void OnPointerExit(PointerEventData eventData)
        {
            if (!origin.canStore) return;
            inventoryManager.mouseStorageExit(this);
        }

        //internal void setData(ItemLevel baseData)
        //{
        //    myData = (ItemData)baseData.myData.Clone();
        //}
    }
}