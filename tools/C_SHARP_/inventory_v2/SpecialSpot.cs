using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
namespace playerInventory
{
    public class SpecialSpot : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler
    {
        PlayerInventory inventoryManager;
        public Transform objectTransform;
        public Item Item;
        public spotPlace filterTag;
        void Start()
        {
            inventoryManager = GameObject.Find("PlayerScripts").GetComponent<PlayerInventory>();
        }
        public void OnPointerEnter(PointerEventData eventData)
        {
            inventoryManager.mouseSpecialEnter(this);
        }
        public void OnPointerExit(PointerEventData eventData)
        {
            inventoryManager.mouseSpecialExit(this);
        }
        void Update()
        {
        }
    }
}