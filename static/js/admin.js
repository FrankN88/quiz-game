function delete_question(id){
      if(!confirm("Delete this element?")) return;
      window.open("/delete_question?id_question="+id,"_self");
}


function delete_user(id){
      if(!confirm("Delete this element?")) return;
      window.open("/delete_user?id_user="+id,"_self");
}